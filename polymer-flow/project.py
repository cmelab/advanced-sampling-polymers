"""Define the project's workflow logic and operation functions.

Execute this script directly from the command line, to view your project's
status, execute operations and submit them to a cluster. See also:

    $ python src/project.py --help
"""
import sys

from flow import FlowProject, directives
from flow.environment import DefaultSlurmEnvironment

sys.path.append("..")

from src.molecules import PPS, PolyEthylene

MOLECULES_TYPES = {"PPS": PPS,
                   "PolyEthylene": PolyEthylene
                   }


class MyProject(FlowProject):
    pass


class Borah(DefaultSlurmEnvironment):
    hostname_pattern = "borah"
    template = "borah.sh"

    @classmethod
    def add_args(cls, parser):
        parser.add_argument(
            "--partition",
            default="shortgpu",
            help="Specify the partition to submit to."
        )


class R2(DefaultSlurmEnvironment):
    hostname_pattern = "r2"
    template = "r2.sh"

    @classmethod
    def add_args(cls, parser):
        parser.add_argument(
            "--partition",
            default="shortgpuq",
            help="Specify the partition to submit to."
        )


class Fry(DefaultSlurmEnvironment):
    hostname_pattern = "fry"
    template = "fry.sh"

    @classmethod
    def add_args(cls, parser):
        parser.add_argument(
            "--partition",
            default="batch",
            help="Specify the partition to submit to."
        )


# Definition of project-related labels (classification)
@MyProject.label
def sampled(job):
    return job.doc.get("done")


@MyProject.label
def initialized(job):
    return job.isfile("trajectory.gsd")


@directives(executable="python -u")
@directives(ngpu=1)
@MyProject.operation
@MyProject.post(sampled)
def sample(job):
    from src.system import System
    from src.simulation import Simulation
    import foyer

    with job:
        print("-----------------------")
        print("JOB ID NUMBER:")
        print(job.id)
        print("-----------------------")
        print("----------------------")
        print("Creating the system...")
        print("----------------------")

        # Set up system parameters
        sys = System(molecule=MOLECULES_TYPES[job.sp.molecule], n_mols=job.sp.n_mols,
                     chain_lengths=job.sp.chain_lengths, density=job.sp.density)
        if job.sp.system_type == "pack":
            sys.pack()
        else:
            raise ValueError("Only pack configuration building function is supported! Use `pack` for `system_type`.")
        ff = foyer.Forcefield(name=job.sp.forcefield)
        sys.apply_forcefield(forcefield=ff)

        print("----------------------")
        print("System generated...")
        print("----------------------")
        print("----------------------")
        print("Starting simulation...")
        print("----------------------")
        sim = Simulation(system=sys.typed_system, dt=job.sp.dt, r_cut=job.sp.r_cut, seed=job.sp.sim_seed,
                         auto_scale=True)
        job.doc['ref_energy'] = sim.ref_energy
        job.doc['ref_distance'] = sim.ref_distance
        job.doc['ref_mass'] = sim.ref_mass
        job.doc['steps_per_frame'] = sim.gsd_write_freq
        job.doc['steps_per_log'] = sim.log_write_freq

        print("------------------------------")
        print("Simulation object generated...")
        print("------------------------------")
        print("----------------------------")
        print("Running shrink simulation...")
        print("----------------------------")

        sim.run_shrink(
            kT=job.sp.shrink_kT,
            final_box_lengths=sys.target_box * 10 / sim.ref_distance,
            n_steps=job.sp.shrink_steps,
            tau_kt=job.sp.tau_kT,
            period=job.sp.shrink_period,
        )

        job.doc["shrink_done"] = True

        print("----------------------------")
        print("Running NVT simulation...")
        print("----------------------------")

        sim.run_NVT(n_steps=job.sp.NVT_steps, kT=job.sp.NVT_kT, tau_kt=job.sp.tau_kT)
        job.doc["NVT_done"] = True

        job.doc["final_timestep"] = sim.sim.timestep
        job.doc["done"] = True

        print("-----------------------------")
        print("Simulation finished completed")
        print("-----------------------------")


if __name__ == "__main__":
    MyProject().main()
