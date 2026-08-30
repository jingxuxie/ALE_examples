# Clifford Mirror RB Experiments on IBM Q Processors

This folder contains all the mirror RB experimental data presented in the paper, from
experiments on IBM Q Quito and IBM Q Rueschlikon, and the code used to analyze that
data. This code generates the plots shown in Figures 1, 3 and 4 of the paper.

## Table of Contents

This directory contains two folders:

- `ibmq_quito`: The data from IBM Q Quito, stored in the pyGSTi ExperimentDesign format.
- `ibmq_rueschlikon`: The data from IBM Q Rueschlikon, stored in the pyGSTi ExperimentDesign format.

This directory contains two Jupyter notebooks:

- `ibmq_quito.ipynb`
- `imbq_rueschlikon.ipynb`

which perform the data analysis (using pyGSTi) and create the plots.

## Software

This data was analyzed using the PyGSTi package on commit `6c55a226b787b8758fe76090ce1a9185aad7b6cd`.