from itertools import combinations_with_replacement as combo
import operator
import os

import gsd.hoomd
import hoomd
import hoomd.md
from mbuild.formats.hoomd_forcefield import create_hoomd_forcefield
import numpy as np
import parmed as pmd


class Simulation:
    """The simulation context management class.

    This class takes the output of the Initialization class
    and sets up a hoomd-blue simulation.

    Parameters
    ----------
    system : Parmed Structure 
        The typed system created in system.py 
    r_cut : float, default 2.5
        Cutoff radius for potentials (in simulation distance units)
    dt : float, default 0.0001
        Initial value for dt, the ize of simulation timestep
    auto_scale : bool, default True
        Set to true to use reduced simulation units.
        distance, mass, and energy are scaled by the largest value
        present in the system for each.
    gsd_write : int, default 1e4
        Period to write simulation snapshots to gsd file.
    gsd_file_name : str, default "trajectory.gsd"
        The file name to use for the GSD file
    log_write : int, default 1e3
        Period to write simulation data to the log file.
    log_file_name : str, default "sim_data.txt"
        The file name to use for the .txt log file
    seed : int, default 42
        Seed passed to integrator when randomizing velocities.
    restart : str, default None
        Path to gsd file from which to restart the simulation
    
    Methods
    -------

    """
    def __init__(
        self,
        system,
        r_cut=2.5,
        dt=0.0003,
        auto_scale=True,
        seed=42,
        restart=None,
        pppm_kwargs={"Nx": 16, "Ny": 16, "Nz": 16},
        gsd_write_freq=1e4,
        gsd_file_name="trajectory.gsd",
        log_write_freq=1e3,
        log_file_name="sim_data.txt"
    ):
        self.system = system
        self.r_cut = r_cut
        self._dt = dt
        self.auto_scale = auto_scale
        self.gsd_write_freq = gsd_write_freq
        self.log_write_freq = log_write_freq
        self.gsd_file_name = gsd_file_name
        self.log_file_name = log_file_name
        self.ref_mass = max([atom.mass for atom in self.system.atoms])
        pair_coeffs = list(set(
            (atom.type, atom.epsilon, atom.sigma)for atom in self.system.atoms
                        )
        )
        self.ref_energy = max(pair_coeffs, key=operator.itemgetter(1))[1]
        self.ref_distance = max(pair_coeffs, key=operator.itemgetter(2))[2]
        self.restart = restart
        self.pppm_kwargs = pppm_kwargs
        self.log_quantities = [
            "kinetic_temperature",
            "potential_energy",
            "kinetic_energy",
            "volume",
            "pressure",
            "pressure_tensor",
        ]
        self.device = hoomd.device.auto_select()
        self.sim = hoomd.Simulation(device=self.device, seed=seed)
        self.all = hoomd.filter.All()
        self.integrator = None
        # Create forcefield objects and initial snapshot from self.system
        self.init_snap, self.forcefield, refs = create_hoomd_forcefield(
                structure=self.system,
                r_cut=self.r_cut,
                auto_scale=self.auto_scale,
                pppm_kwargs=self.pppm_kwargs 
        )
        if self.restart:
            self.sim.create_state_from_gsd(self.restart)
        else:
            self.sim.create_state_from_snapshot(self.init_snap)
        # Add a gsd and thermo props logger to sim operations
        self._add_hoomd_writers()

    @property
    def nlist(self):
        return self.forcefield[0].nlist

    @nlist.setter
    def nlist(self, hoomd_nlist, buffer=0.4):
        self.forcefield[0].nlist = hoomd_nlist(buffer)

    @property
    def dt(self):
        return self._dt
    
    @dt.setter
    def dt(self, value):
        self._dt = value
        if self.integrator:
            self.sim.operations.integrator.dt = self.dt

    @property
    def method(self):
        if self.integrator:
            return self.sim.operations.integrator.methods[0]
        else:
            raise RuntimeError(
                    "No integrator, or method has been set yet. "
                    "These will be set once one of the run functions "
                    "have been called for the first time."
            )

    def set_integrator_method(self, integrator_method, method_kwargs):
        """Creates an initial (or updates the existing) method used by
        Hoomd's integrator. This doesn't need to be called directly;
        instead the various run functions use this method to update
        the integrator method as needed.

        Parameters:
        -----------
        integrrator_method : hoomd.md.method; required
            Instance of one of the hoomd.md.method options
        method_kwargs : dict; required
            A diction of parameter:value for the integrator method used

        """
        if not self.integrator: # Integrator and method not yet created
            self.integrator = hoomd.md.Integrator(dt=self.dt)
            self.integrator.forces = self.forcefield
            self.sim.operations.add(self.integrator)
            new_method = integrator_method(**method_kwargs) 
            self.sim.operations.integrator.methods = [new_method]
        else: # Replace the existing integrator method
            self.integrator.methods.remove(self.method)
            new_method = integrator_method(**method_kwargs)
            self.integrator.methods.append(new_method)

    def run_shrink(
            self,
            n_steps,
            period,
            kT,
            tau_kt,
            final_box_lengths,
            thermalize_particles=True
    ):
        """Runs an NVT simulation while shrinking the simulation volume
        to a desired final volume.

        Note:
        -----
        When determining final box lengths, make sure to acount for
        the reference distance (Simulation.ref_distance)
        if auto scaling was used

        Parameters:
        -----------
        n_steps : int, required
            Number of steps to run during shrinking
        period : int, required
            The number of steps ran between box updates
        kT : int or hoomd.variant.Ramp; required
            The temperature to use during shrinking. 
        tau_kt : float; required
            Thermostat coupling period (in simulation time units)
        final_box_lengths : np.ndarray, shape=(3,), dtype=float; required
            The final box edge lengths in (x, y z) order

        """
        # Set up box resizer
        resize_trigger = hoomd.trigger.Periodic(period)
        box_ramp = hoomd.variant.Ramp(
                A=0, B=1, t_start=self.sim.timestep, t_ramp=int(n_steps)
        )
        initial_box = self.sim.state.box
        final_box = hoomd.Box(
                Lx=final_box_lengths[0],
                Ly=final_box_lengths[1],
                Lz=final_box_lengths[2]
        )
        box_resizer = hoomd.update.BoxResize(
                box1=initial_box,
                box2=final_box,
                variant=box_ramp,
                trigger=resize_trigger
        )
        self.sim.operations.updaters.append(box_resizer)
        self.set_integrator_method(
                integrator_method=hoomd.md.methods.NVT,
                method_kwargs={"tau": tau_kt, "filter": self.all, "kT": kT},
        )
        if thermalize_particles:
            self._thermalize_system(kT)
        self.sim.run(n_steps)
    
    def run_langevin(
            self,
            n_steps,
            kT,
            alpha,
            tally_reservoir_energy=False,
            default_gamma=1.0,
            default_gamma_r=(1.0, 1.0, 1.0),
            thermalize_particles=True
    ):
        """"""
        self.set_integrator_method(
                integrator_method=hoomd.md.methods.Langevin,
                method_kwargs={
                        "filter": self.all,
                        "kT": kT,
                        "alpha": alpha,
                        "tally_reservoir_energy": tally_resivoir_energy,
                        "default_gamma": default_gamma,
                        "default_gamma_r": default_gamma_r,
                    }
        )
        if thermalize_particles:
            self._thermalize_system(kT)
        self.run(n_steps)

    def run_NPT(
            self,
            n_steps,
            kT,
            pressure,
            tau_kt,
            tau_pressure,
            couple="xyz",
            box_dof=[True, True, True, False, False, False],
            rescale_all=False,
            gamma=0.0,
            thermalize_particles=True
    ):
        """"""
        self.set_integrator_method(
                integrator_method=hoomd.md.methods.NPT,
                method_kwargs={
                    "kT": kT,
                    "S": pressure,
                    "tau": tau_kt,
                    "tauS": tau_pressure,
                    "couple": couple,
                    "box_dof": box_dof,
                    "rescale_all": rescale_all,
                    "gamma": gamma,
                    "filter": self.all,
                    "kT": kT
                }
        )
        if thermalize_particles:
            self._thermalize_system(kT)
        self.sim.run(n_steps)

    def run_NVT(self, n_steps, kT, tau_kt, thermalize_particles=True):
        """"""
        self.set_integrator_method(
                integrator_method=hoomd.md.methods.NVT,
                method_kwargs={"tau": tau_kt, "filter": self.all, "kT": kT},
        )
        if thermalize_particles:
            self._thermalize_system(kT)
        self.sim.run(n_steps)

    def run_NVE(self, n_steps):
        """"""
        self.set_integrator_method(
                integrator_method=hoomd.md.methods.NVE,
                method_kwargs={"filter": self.all}
        )
        self.sim.run(n_steps)

    def temperature_ramp(self, n_steps, kT_start, kT_final):
        return hoomd.variant.Ramp(
                A=kT_init,
                B=kT_final,
                t_start=self.sim.timestep,
                t_ramp=int(n_steps)
        )

    def _thermalize_system(self, kT):
        if isinstance(kT, hoomd.variant.Ramp):
            self.sim.state.thermalize_particle_momenta(
                    filter=self.all, kT=kT.range[0]
            )
        else:
            self.sim.state.thermalize_particle_momenta(filter=self.all, kT=kT)

    def _add_hoomd_writers(self):
        """Creates gsd and log writers"""
        gsd_writer = hoomd.write.GSD(
                filename=self.gsd_file_name,
                trigger=hoomd.trigger.Periodic(int(self.gsd_write_freq)),
                mode="wb",
                dynamic=["momentum"]
        )

        logger = hoomd.logging.Logger(categories=["scalar", "string"])
        logger.add(self.sim, quantities=["timestep", "tps"])
        thermo_props = hoomd.md.compute.ThermodynamicQuantities(filter=self.all)
        self.sim.operations.computes.append(thermo_props)
        logger.add(thermo_props, quantities=self.log_quantities)

        for f in self.forcefield:
            logger.add(f, quantities=["energy"])

        table_file = hoomd.write.Table(
            output=open(self.log_file_name, mode="w", newline="\n"),
            trigger=hoomd.trigger.Periodic(period=int(self.log_write_freq)),
            logger=logger,
            max_header_len=None,
        )
        self.sim.operations.writers.append(gsd_writer)
        self.sim.operations.writers.append(table_file)
