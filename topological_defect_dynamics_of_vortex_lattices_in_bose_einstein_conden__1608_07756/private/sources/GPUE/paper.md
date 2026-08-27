---
title: 'GPUE: Graphics Processing Unit Gross--Pitaevskii Equation solver'
tags:
  - CUDA
  - physics
  - dynamics
  - quantum
  - nonlinear
  - Bose-Einstein condensate
authors:
  - name: James R. Schloss
    orcid: 0000-0002-3243-8918
    affiliation: 1
  - name: Lee J. O'Riordan
    orcid: 0000-0002-6758-9433
    affiliation: 1
affiliations:
 - name: Okinawa Institute of Science and Technology Graduate University, Onna-son, Okinawa 904-0495, Japan.
   index: 1
date: 10 December 2018
bibliography: paper.bib
---

# Summary

Bose--Einstein Condensates (BECs) are superfluid systems consisting of bosonic atoms that have been cooled and condensed into a single, macroscopic ground state [@PethickSmith2008; @FetterRMP2009].
These systems can be created in an experimental laboratory and allow for the the exploration of physical phenomenon such as superfluid turbulence [@Roche2008; @White2014; @Navon2016], chaotic dynamics [@Gardiner2002; @Kyriakopoulos2014; @Zhang2017], and analogues of other quantum systems [@DalibardRMP2011].
Numerical simulations of BECs that directly mimic experiments are valuable to fundamental research in these areas and allow for theoretical advances before experimental validation.
The dynamics of BEC systems can be found by solving the non-linear Schr&ouml;dinger equation known as the Gross--Pitaevskii Equation (GPE),

$$
i\hbar \frac{\partial\Psi(\mathbf{r},t)}{\partial t} = \left( -\frac{\hbar^2}{2m} {\nabla^2} + V(\mathbf{r}) + g|\Psi(\mathbf{r},t)|^2\right)\Psi(\mathbf{r},t),
$$

where $\Psi(\mathbf{r},t)$ is the three-dimensional many-body wavefunction of the quantum system, $\mathbf{r} = (x,y,z)$, $m$ is the atomic mass, $V(\mathbf{r})$ is an external potential, $g = \frac{4\pi\hbar^2a_s}{m}$ is a coupling factor, and $a_s$ is the scattering length of the atomic species.
Here, the GPE is shown in three dimensions, but it can easily be modified to one or two dimensions [@PethickSmith2008].
One of the most straightforward methods for solving the GPE is the split-operator method, which has previously been accelerated with GPU devices [@Ruf2009; @Bauke2011].
No software packages are available using this method on GPU devices that allow for user-configurable simulations and a variety of different system types; however,
several software packages exist to simulate BECs with other methods and on different architectures, including GPELab [@Antoine2014] the Massively Parallel Trotter-Suzuki Solver [@Wittek2013], and XMDS [@xmds].

GPUE is a GPU-based Gross--Pitaevskii Equation solver via the split-operator method for superfluid simulations of both linear and non-linear Schr&ouml;dinger equations, emphasizing superfluid vortex dynamics in two and three dimensions. GPUE is a fast, robust, and accessible software suite to simulate physics for fundamental research in the area of quantum systems and has been used to manipulate large vortex lattices in two dimensions [@ORiordan2016; @ORiordan2016b] along with ongoing studies of vortex dynamics.

For these purposes, GPUE provides a number of unique features:
1. Dynamic field generation for trapping potentials and other variables on the GPU device.
2. Vortex tracking in 2D and vortex highlighting in 3D.
3. Configurable gauge fields for the generation of artificial magnetic fields and corresponding vortex distributions [@DalibardRMP2011; @Ghosh2014].
4. Vortex manipulation via direct control of the wavefunction phase [@Dobrek1999].

All of these features enable GPUE to simulate a wide variety of linear and non-linear dynamics of quantum systems.
GPUE additionally features a numerical solver that improves on other available suites [@WittekGPE2016; @ORiordan2017].
All of GPUE's features and functionality have been described in further detail in the documentation [@documentation].

# Acknowledgements
This work has been supported by the Okinawa Institute of Science and Technology Graduate University and by JSPS KAKENHI Grant Number JP17J01488.
We would also like to thank Thomas Busch, Rashi Sachdeva, Tiantian Zhang, Albert Benseney, and Angela White for discussions on useful physical systems to simulate with the GPUE codebase, along with Peter Wittek and Tadhg Morgan for contributions to the code, itself.
These acknowledgements can be found in `GPUE/acknowledgements.md`.

# References
