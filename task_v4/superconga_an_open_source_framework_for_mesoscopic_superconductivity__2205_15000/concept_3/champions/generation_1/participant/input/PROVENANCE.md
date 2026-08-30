# Scientific seed and limits

Primary sources checked August 27, 2026:

1. P. Holmvall et al., *SuperConga: An open-source framework for mesoscopic
   superconductivity*, arXiv:2205.15000 (May 30, 2022; accepted revision February
   15, 2023), Applied Physics Reviews 10, 011317 (2023), DOI 10.1063/5.0100324.
   The relevant seed is spatially resolved spectroscopy/LDOS and vortex physics
   in finite two-dimensional singlet superconductors, not the task's inverse algorithm.
   Source: `https://arxiv.org/abs/2205.15000`.
2. The official SuperConga documentation describes its quasiclassical,
   self-consistent framework and interactive spectroscopy, and lists the
   microscopic BdG comparison in its research bibliography.
   Source: `https://superconga.gitlab.io/superconga-doc/about.html`.
3. N. Wall Wennerdal et al., *Breaking time-reversal and translational symmetry
   at edges of d-wave superconductors: Microscopic theory and comparison with
   quasiclassical theory*, Physical Review Research 2, 043198 (November 6, 2020),
   arXiv:2006.00456, DOI 10.1103/PhysRevResearch.2.043198. It uses exact tight-binding
   BdG diagonalization and compares with quasiclassics. It is an official-listed
   companion/comparison study, **not chronologically a follow-up to the 2022 paper**.
   Source: `https://arxiv.org/abs/2006.00456`.

This benchmark newly defines a microscopic diagnostic reduced problem: a small,
open-boundary, onsite s-wave lattice with prescribed vortex cores and scalar
impurities. It is not a reproduction of the comparison paper's d-wave edge-state
phase transition, not SuperConga's native quasiclassical solver, and not a claim
of predictive material realism. Non-self-consistency and neglect of the vector
potential are deliberate reductions. The exact forward/inverse distinction and
experiment-selection budget, rather than microscopic realism, define the task.
