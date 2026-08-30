# Private generation provenance

Sources inspected on 2026-08-28. These notes and private generation artifacts are not mounted for tournament participants.

- Margine and Giustino, arXiv:1211.3345, HTML full text: https://arxiv.org/html/1211.3345 . Equations (18)-(23) define spectral kernels and the Fermi-surface-restricted nonlinear system; Section II.2 discusses anisotropic Coulomb and constant-DOS limitations; Section III.2 discusses critical slowing of self-consistency and approximate versus iterative continuation. These are scientific seeds, not a claim that the synthetic challenges reproduce a particular material.
- Official EPW theory: https://docs.epw-code.org/Theory.html . Current normal/full-bandwidth conventions and superconductivity equations were inspected.
- Official EPW releases: https://docs.epw-code.org/Releases.html . Sparse intermediate-representation sampling in v5.9, older superconductivity mixing/restart fixes, and subsequent release history were inspected. No undocumented issue is an evaluation condition.
- Official Quantum ESPRESSO EPW source: https://raw.githubusercontent.com/QEF/q-e/develop/EPW/src/supercond_aniso.f90 . The simple FSR summation uses positive-frequency difference/sum kernels and the Coulomb factor of two; a separate FFT implementation highlights that efficient summation is an established baseline, not the whole research task.
- Follow-up: Mori et al., Efficient anisotropic Migdal-Eliashberg calculations with the Intermediate Representation basis and Wannier interpolation, arXiv:2404.11528, https://arxiv.org/abs/2404.11528 . Inspected as evidence that frequency-scale separation and Coulomb retardation remain substantive computational concerns.

The final packages use newly authored finite-dimensional models and evaluators. No EPW implementation is presented as original code, and the participant mission is not to reproduce EPW.
