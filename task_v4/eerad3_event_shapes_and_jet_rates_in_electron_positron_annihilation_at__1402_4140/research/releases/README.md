# EERAD3

Parton-level Monte-Carlo generator for Z boson and Higgs decays to b-quarks and gluons.

## Overview

EERAD3 performs calculations up to third order in off-shell photon/Z-boson
decays and hadronic Higgs decays to massless b-quarks (with non-vanishing
Yukawa coupling) and gluons (via an effective Higgs-gluon coupling).
This includes:
- off-shell photon decays to 3 jets up to NNLO
- Higgs decays to massless b-quarks with 3 and 4 jets up to NLO
- Higgs decays to gluons with 3 and 4 jets up to NLO

## Repository

The repository is organised as follows:
- The `src/` folder contains all source code for the main EERAD3 executables (see below)
- The `pyext/` folder contains auxilliary python scripts for data and histogram
handling, and plotting as well as a python API for the main EERAD3 code
- The `bin/` folder contains all executables (after compilation, see below)
- The `examples/` folder contains example setups showing the use of EERAD3

The `src/` directory is organised into the following directories:
- `core/` containing the general parts of EERAD3
- `analyses/` containing subroutines and modules for (custom) analyses
- `Zqq/` containing files specific to off-shell photon/Z-boson decays
- `Hbb/` containing files specific to Higgs decays to b-quarks
- `Hgg/` containing files specific to Higgs decays to gluons

## Installation

To compile EERAD3, simply run `make [-j <ncores>]`, where `-j` is an optional
command-line argument to specify the number of available CPU cores `<ncores>`.

## Running EERAD3

The main executable is called `eerad3` and located in the `bin/` directory.
To start EERAD3, run

`./eerad3 -i <eerad3_runcard>`

where `-i <eerad3_runcard>` specifies the run card, see examples below.
This will produce histograms of the perturbative coefficients
`A` (for LO), `B` (for NLO), and `C` (for NNLO), excluding factors
of the strong coupling constant.

To produce differential histograms, the python `eerad3hist` program
can be used, which is place in the `bin/` directory upon compilation.
To make distributions from histograms with `eerad3hist`, run

`./eerad3hist makedist <makedist_card>`

where `<makedist_card>` specifies the card containing standard-model
parameters and histogram input.
Note that this is not the same run card as for the `eerad3` executable.

The `merge` command of the `eerad3hist` script can be used to combine
multiple statistically independent EERAD3 runs. The `merge` command
automatically identifies statistically independent histograms for the
same observable and combines them into a single histogram.
To use the `merge` command, run

`./eerad3hist merge <result_directory>`

where `<result_directory>` specifies the directory in which the
resulting histograms are saved.
The output of `merge` can be used as input for `combine`.

To combine V and R contributions to NLO histograms as well as
VV, RV, and RR contributions to NNLO histograms, the `combine` command
in `eerad3hist` can be used. For a given perturbative order,
the `combine` command automatically identifies the relevant histograms
per observable and combines them into histogram of the respective
perturbative coefficient A, B, or C.
To use the `combine` command, run

`./eerad3hist combine <result_directory>`

where `<result_directory>` specifies the directory in which the
histograms for the `A`, `B`, and `C` coefficients are saved.
The output of `combine` can be used as input for `makedist`.

### Examples

Example setups for both Higgs and Z-boson and Higgs decays are
contained in the `examples/` directory. They are labelled by
the leading-order (2-body) decay of the colour-singlet resonance
and the number of hard jets.
Currently available setups are:
- `zqq_3j/` (event shapes in Z decays to 3 jets up to NNLO)
- `zqq_4j/` (event shapes in Z decays to 4 jets up to NLO)
- `hbb_3j/` (event shapes in the b-quark channel in H decays to 3 jets up to NLO)
- `hgg_3j/` (event shapes in the gluon channel in H decays to 3 jets up to NLO)
- `hbb_4j/` (event shapes in the b-quark channel in H decays to 4 jets up to NLO)
- `hgg_4j/` (event shapes in the gluon channel in H decays to 4 jets up to NLO)

The examples can be run by navigating to the respective directory and executing

`./eerad3 -i run.<LO|V|R|VV|RV|RR>.input`

for the respective LO, V, R, VV, RV, or RR contribution.

### Observables

A number of observables are implemented in EERAD3 by default.
This includes
- thrust, thrust minor
- C- and D-parameter
- heavy-jet and light-jet mass
- total, wide, and narrow jet broadening
- Durham three-jet resolutions y23D, y34D, and y45D
- Durham three-, four-, and five-jet rates R3D, R4D, and R5D
- fractional energy correlators FC_x with x=0, 0.5, 1.0, 1.5
- soft-drop thrust with zcut=0.1 and beta=0, beta=1, and beta=2

A prototype of a custom analysis can be found in `myanalysis.f90` in
`src/analyses/`. Every user analysis has to include the subroutines
- `initanalysis` to initialise the analysis and book histograms
- `ecuts_ana` to calculate the observables and apply cuts
- `fillhists` to fill the histograms
- `getvar` to fetch a variable for phase-space weighting
EERAD3 can be compiled against a user analysis by setting the
environment variable `ANALYSIS` to the analysis name, e.g.,

`make [-j <ncores>] ANALYSIS=myanalysis.f90`