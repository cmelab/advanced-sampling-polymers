import foyer
from pkg_resources import resource_filename

class GAFF(foyer.Forcefield):
    def __init__(self, forcefield_files="library/forcefields/gaff.xml"):
        super(GAFF, self).__init__(forcefield_files=forcefield_files)
        self.description = (
                "The General Amber Forcefield written in foyer XML format. "
                "The XML file was obtained from the antefoyer package: "
                "https://github.com/rsdefever/antefoyer/tree/master/antefoyer"
        )

class OPLS_AA(foyer.Forcefield):
    def __init__(self, name="oplsaa"):
        super(OPLS_AA, self).__init__(name=name)
        self.description = (
                "opls-aa forcefield found in the Foyer package"
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
