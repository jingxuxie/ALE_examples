Simple demonstration code for shift-invert diagonalization of a disordered XXZ chain.
=====================================================================================

This code provides very basic functionality to generate the sparse Hamiltonian of the spin 1/2 XXZ chain in a distributed way. 
Since we are concerned with shift-invert diagonalization limited to small system sizes, the basis is fully enumerated in a 
symmetry sector with fixed total magnetization to make the code easier to read. We also provide a code to measure diagonal operators (local Sz).

The main program sinvert.cc uses these data structures to communicate with the PETSC/SLEPC libraries to calculate interior eigenpairs of the Hamiltonian and local observables measured in these states.


The code is licenced with GPL v3. If you need further documentations and installation instructions, **please refer to the accompanying paper**:

[1] Francesca Pietracaprina, Nicolas Mace, David J. Luitz and Fabien Alet,    
*["Shift-invert diagonalization of large many-body localizing spin chains"](https://scipost.org/SciPostPhys.5.5.045/pdf)*,     
**[SciPost Phys. 5, 045 (2018)](https://scipost.org/SciPostPhys.5.5.045)**

In case you use this code for academic purposes, please include a reference to this paper [1] in relevant publications.
