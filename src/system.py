import mbuild as mb
import numpy as np


class System:
    def __init__(
            self,
            molecule,
            n_mols,
            chain_lengths,
            density,
            united_atom=False
    ):
        self.density = density
        self.n_mols = n_mols
        self.chain_lengths = chain_lengths
        self.united_atom = united_atom
        self.system = None
        self.typed_system = None
        self.target_box = None
        self.mass = 0
        self.chains = []
        for n, l in zip(n_mols, chain_lengths):
            for i in range(n):
                chain = molecule(length=l)
                self.mass += chain.mass
                self.chains.append(chain)

    def pack(self, expand_factor=5):
        self.set_target_box()
        self.system = mb.packing.fill_box(
                compound=self.chains,
                n_compounds=[1 for i in self.chains],
                box=(self.target_box * expand_factor).tolist(),
                overlap=0.2,
                edge=0.2
        )
    
    def set_target_box(
            self, x_constraint=None, y_constraint=None, z_constraint=None
    ):
        """Set the target volume of the system used during
        a shrink simulation run.
        If no constraints are set, the target box is cubic.
        Setting constraints will hold those box vectors
        constant and adjust others to match the target density.

        Parameters
        -----------
        x_constraint : float, optional, defualt=None
            Fixes the box length (nm) along the x axis
        y_constraint : float, optional, default=None
            Fixes the box length (nm) along the y axis
        z_constraint : float, optional, default=None
            Fixes the box length (nm) along the z axis

        """
        if not any([x_constraint, y_constraint, z_constraint]):
            Lx = Ly = Lz = self._calculate_L()
        else:
            constraints = np.array([x_constraint, y_constraint, z_constraint])
            fixed_L = constraints[np.where(constraints!=None)]
            #Conv from nm to cm for _calculate_L
            fixed_L *= 1e-7
            L = self._calculate_L(fixed_L=fixed_L)
            constraints[np.where(constraints==None)] = L
            Lx, Ly, Lz = constraints

        self.target_box = np.array([Lx, Ly, Lz])

    def apply_forcefield(self, forcefield):
        self.typed_system = forcefield.apply(self.system)
        if self.united_atom:
            print("Removing hydrogen atoms and adjusting heavy atoms")
            hydrogens = [a for a in self.typed_system.atoms if a.element == 1]
            for h in hydrogens:
                bonded_atom = h.bond_partners[0]
                bonded_atom.mass += h.mass
                bonded_atom.charge += h.charge
            self.typed_system.strip(
                    [a.atomic_number == 1 for a in self.typed_system.atoms]
            )

    def _calculate_L(self, fixed_L=None):
        """Calculates the required box length(s) given the
        mass of a sytem and the target density.

        Box edge length constraints can be set by set_target_box().
        If constraints are set, this will solve for the required
        lengths of the remaining non-constrained edges to match
        the target density.

        Parameters
        ----------
        fixed_L : np.array, optional, defualt=None
            Array of fixed box lengths to be accounted for
            when solving for L

        """
        # Convert from amu to grams
        M = self.mass * 1.66054e-24
        vol = (M / self.density) # cm^3
        if fixed_L is None:
            L = vol**(1/3)
        else:
            L = vol / np.prod(fixed_L)
            if len(fixed_L) == 1: # L is cm^2
                L = L**(1/2)
        # Convert from cm back to nm
        L *= 1e7
        return L
    
    def visualize(self):
        if self.system:
            return self.system.visualize()
        else:
            raise ValueError(
                    "The system configuration hasn't been initialzed yet. "
            )
