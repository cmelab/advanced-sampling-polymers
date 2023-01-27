#!/usr/bin/env python
"""Initialize the project's data space.

Iterates over all defined state points and initializes
the associated job workspace directories.
The result of running this file is the creation of a signac workspace:
    - signac.rc file containing the project name
    - signac_statepoints.json summary for the entire workspace
    - workspace/ directory that contains a sub-directory of every individual statepoint
    - signac_statepoints.json within each individual statepoint sub-directory.

"""

import logging
from collections import OrderedDict
from itertools import product

import signac


def get_parameters():
    parameters = OrderedDict()
    
    ### SYSTEM GENERATION PARAMETERS ###
    parameters["molecule"] = ["PPS", "PolyEthylene"]
    parameters["n_mols"] = [[50]]
    parameters["chain_lengths"] = [[6]]
    parameters["density"] = [1.27]
    parameters["system_type"] = [
        "pack",
    ]
    parameters["forcefield"] = ["oplsaa"]
    parameters["box_constraints"] = [
        {"x": None, "y": None, "z": None}
    ]
    parameters["kwargs"] = [
        {"expand_factor": 7},
        # {"n": 4, "a": 1.5, "b": 1.5}
    ]
    ### SIMULATION PARAMETERS ###
    parameters["tau_kT"] = [0.1]
    parameters["tau_p"] = [0.1]
    parameters["sim_seed"] = [42]
    parameters["dt"] = [0.0003]

    parameters["shrink_kT"] = [0.5]
    parameters["shrink_steps"] = [1e4]
    parameters["shrink_period"] = [100]

    parameters["NPT_kT"] = [1.0]
    parameters["NPT_steps"] = [1e6]
    parameters["NPT_p"] = [0.001]

    parameters["NVT_kT"] = [1.0]
    parameters["NVT_steps"] = [1e6]

    parameters["r_cut"] = [2.5]
    parameters["e_factor"] = [0.5]

    return list(parameters.keys()), list(product(*parameters.values()))


custom_job_doc = {}  # add keys and values for each job document created


def main():
    project = signac.init_project("polymers")  # Set the signac project name
    param_names, param_combinations = get_parameters()
    # Create the generate jobs
    for params in param_combinations:
        parent_statepoint = dict(zip(param_names, params))
        parent_job = project.open_job(parent_statepoint)
        parent_job.init()
        parent_job.doc.setdefault("done", False)

    if custom_job_doc:
        for key in custom_job_doc:
            parent_job.doc.setdefault(key, custom_job_doc[key])

    project.write_statepoints()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
