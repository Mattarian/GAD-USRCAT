# GAD-USRCAT

## Using the GA-D
This repository contains the necessary edited code for the use of the GA-D (developed by https://github.com/aspuru-guzik-group/GA) with USRCAT and Tanimoto scoring.

To use this repository:
1. Download or clone a version of the original GA-D code (https://github.com/aspuru-guzik-group/GA)
2. Go to the relevent "experiment" code, and replace the .py files with the edited .py files provided in this repository
3. Run the code as normal, with the new repository

It is important to note that the core-ga.py file contains all the parameters to control the direction of evolution by the algorithm. (eg. number of gens, size of populations etc.)

The most common error when running the code is an rdkit error, which is the product of USRCAT calculations being unable to handle atoms in certain positions/arrangements in the generated molecular structures. If this error occurs, the code will attempt to fix it by moving to a more liberal selection of Force Field parameters during calculation, leading to slight discrepancies in results. As of the time of writing a method of correcting this is not known, as the only viable fix is to run the USRCAT through again with different parameters which is not possible during a run without first stopping and re-attempting.

The parameters of interest in running the code are listed below. These can all be found in core-ga.py:
1. num_generations          : sets generation length (ie. total number of generations for code to run)
2. generation_size          : sets size of population for each generation
3. properties_calc_ls       : sets the parameters to be calculated (this should be all of them, as removing them from this list without removing the relevant parts of the code will raise an error)

# References
A. Nigam, P. Friederich, M. Krenn, A. Aspuru-Guzik, 2019, arxiv preprint, arxiv: arXiv:1909.11655v4
