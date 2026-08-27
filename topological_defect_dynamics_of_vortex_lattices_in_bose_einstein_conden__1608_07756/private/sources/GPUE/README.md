--- 
[logo]: https://github.com/gpue-group/GPUE/blob/master/logo.png "GPUE"
![GPUE - GPU Gross-Pitaevskii Equation solver][logo]

***

[gh]: https://github.com/gpue-group/gpue "GitHub"
[![DOI](http://joss.theoj.org/papers/10.21105/joss.01037/status.svg)](https://doi.org/10.21105/joss.01037)

Welcome to GPUE, the [fastest zero temperature BEC routines in the land](http://peterwittek.com/gpe-comparison.html) (the last time we checked).
All documentation is available at [https://gpue-group.github.io](https://gpue-group.github.io).

## 1. What does this software do?

This software is a CUDA-enabled non-linear Schrodinger (Gross-Pitaevskii) 
equation solver. The primary use of this code was for research on 
Bose-Einstein condensates. Due to the complexity and 
timescales needed to simulate such system, it was essential to write some 
accelerated code to understand the behaviour of such systems. 

As a short introduction of the use-case:
We want to simulate how a Bose-Einstein condensate (BEC) behaves in a trap. 
The trap is parabolic (harmonic), and for the lowest energy state of the 
system (ground-state) the BEC will want to sit about the centre. Due to the
interaction between the particles it will occupy more space than a standard 
Schrodinger equation, which has zero interactions. As a result of these 
interactions many interesting things happen.

The main purpose of the code is to investigate the behaviour of quantum 
vortices (think really small tornadoes). Instead of having a continuous 
range of angular momentum values, the condensate can only accept angular 
momentum in quantised predefined units. 

The most interesting fact is that instead of getting bigger and bigger with 
faster rotation (as a tornado would), these vortices only allow themselves 
to enter with a singular unit of angular momentum (think 100x 1 unit vortices 
instead of 1x 100 unit vortex). This gives us a nice well arranged lattice if 
performed correctly. It is this lattice that we have been researching (read as: 
playing with). However, this code can be used in any trapping geometry, 
rotation, etc. that you wish to use. 

## 2. Great! How do I make a BEC?
See the [Building GPUE](https://gpue-group.github.io/build/) and [GPUE functionality](https://gpue-group.github.io/functionality/)
sections of the documentation.

As an example, here are some simulations performed with the code:
- https://www.youtube.com/playlist?list=PLiRboSbbz10s6cXxvYLFOn3QbmQpdtQVd
- https://youtu.be/68SU_ndFzak

## 3. Specific use-cases
We would like this tool to be a suite for 1D, 2D and 3D simulations of both 
Schrodinger and non-linear Schrodinger (Gross--Pitaevskii) systems. 

## 4. Works using GPUE
If you have used GPUE, or any of the works using GPUE, please consider giving us a citation as:

- James Schloss and Lee James O'Riordan, GPUE: Graphics Processing Unit Gross--Pitaevskii Equation solver. Journal of Open Source Software, 3(32), 1037 (2018), https://doi.org/10.21105/joss.01037

Previous versions of this code/works are citable as follows:

- Lee James O'Riordan et al., GPUE: Phasegineering release, Zenodo. (2016), https://github.com/mlxd/GPUE DOI:10.5281/zenodo.57968

More recent versions will be citable under the [GPUE Group](https://github.com/gpue-group/GPUE) repository. 
Works which have used GPUE include (to-date):
- [Moiré superlattice structures in kicked Bose-Einstein condensates](https://journals.aps.org/pra/abstract/10.1103/PhysRevA.93.023609)
- [Topological defect dynamics of vortex lattices in Bose-Einstein condensates](https://journals.aps.org/pra/abstract/10.1103/PhysRevA.94.053603)
- [Non-equilibrium vortex dynamics in rapidly rotating Bose-Einstein condensates](https://ci.nii.ac.jp/naid/500001054902/)

## 5. Acknowledgements
We are greatly thankful to the support provided by Okinawa Institute of Science 
and Technology Graduate University, without whom this research code would be a 
fraction of what it currently has become. A list of acknowledgements is given in [acknowledgements.md](https://github.com/GPUE-group/GPUE/blob/master/acknowledgements.md).
 
