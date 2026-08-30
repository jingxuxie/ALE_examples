# Source grounding and label audit

Source seed: McClean et al., *OpenFermion: The Electronic Structure Package for
Quantum Computers*, arXiv:1710.07629, v5 (27 February 2019), retrieved 28 August 2026.
Canonical source: `https://arxiv.org/abs/1710.07629`.

Relevant source locations: numerical testing in §I.D (PDF p.6); Fermi–Hubbard
Hamiltonian examples in §I.E (pp.7–8) and model generation in §III (p.18);
`InteractionRDM`, energy contraction, and Eqs.(19–20) in §II.F (pp.14–15).
These motivate finite-sector spectral labels and the RDM consistency audit.
The random families, paired prediction objective, data and thresholds are new
benchmark construction, not results or a dataset claimed by the paper.

No OpenFermion/PySCF dependency is used. The source Hamiltonian convention is
implemented in NumPy/SciPy: fixed-up/fixed-down bit bases, fermionic hopping signs,
sparse Kronecker sums, and the unshifted Hubbard diagonal. Sector dimensions at
8 sites are 4900, 3920, 3920, 3136; at 10 sites, 63504, 52920, 52920, 44100.
`scipy.sparse.linalg.eigsh(which='SA')` seeks each sector ground state, with fixed
independent starting-vector randomness, relative tolerance 2e-11 and residual
acceptance 2e-8 in hopping units. ARPACK nonconvergence aborts generation.
Numerical reference: `https://docs.scipy.org/doc/scipy/reference/generated/scipy.sparse.linalg.eigsh.html`.

`validate_source.py` compares all eigenvalues of five 4-site sectors against an
independent interleaved-spin full-Fock creation/annihilation implementation;
checks the analytic two-site Hubbard dimer, U=0 one-particle gaps and the clean
atomic limit; compares fresh tighter eigensolver restarts for all families and
both sizes; tests simultaneous site permutation and potential-shift invariance;
and reconstructs an energy from 1-RDM and onsite pair occupancy, verifies particle
trace/natural occupations, and checks a Hellmann–Feynman derivative.

`source_validation.json` records independent numerical errors. Every labelled
row also has its four energies, residual norms and wall/CPU timing retained in
`{train,validation,test}_source.npz`. `generation_report.json` includes checksums,
frozen configuration hash, timings and split summaries; `seeds.json` retains
private reproducibility entropy and must never be shipped to participants.

A small residual alone is not a formal certificate that an iterative solver
found the globally lowest root. Independent implementations, analytic limits,
random starts, and tighter restarts supply evidence rather than a proof. Larger
post-generation source checks are recorded separately. No labels are rounded.
