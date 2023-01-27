import foyer

class OPLS_AA(foyer.Forcefield):
    def __init__(self, name="oplsaa"):
        super(OPLSAA, self).__init__(name=name)
        self.description = (
                "Standard opls-aa forcefield found in the Foyer library"
        )


class OPLS_AA_PPS(foyer.Forcefield):
    def __init__(self, forcefield_files="library/forcefields/pps_opls.xml"):
        super(OPLS_AA_PPS, self).__init__(forcefield_files=forcefield_files)
        self.description = (
                "Based on OPLS_AA, trimmed down to include only PPS parameters."
                "One missing parameter was added manually:"
                "<Angle class1=CA class2=S class3=CA angle=1.805 k=627.6/>"
                "The equilibrium angle was determined from experimental PPS papers."
                "The spring constant was used for the equivalent angle in GAFF."
		)
