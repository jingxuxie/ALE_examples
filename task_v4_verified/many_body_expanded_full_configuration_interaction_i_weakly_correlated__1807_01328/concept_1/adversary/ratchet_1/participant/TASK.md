# Adaptive correlation-energy experiments

Build an autonomous policy that estimates the full eight-virtual correlation
energy of a weak-reference paired-electron system from restricted CAS energies.
This is an effective seniority-zero model benchmark, not an ab initio molecular
or Coulomb-integral benchmark.

Assets: `workspace/pair_model.py`, the JSON-lines contract in
`workspace/INTERFACE.md`, 36 labeled practice systems in `input/`, and the
original runnable weak baseline in `baseline/`.

The fixed hidden suite contains 120 systems, equally weighted across six strata.
It includes deliberately conditioned signed-cancellation systems; it is not an
IID draw from the example sampler. The quantitative hidden domain is specified
in `workspace/INTERFACE.md`. The example sampler is illustrative, not a promise
of the hidden distribution. All hidden systems retain reference weight at least
0.94 and excitation gap at least 0.35 hartree.

Submit `solution.py` and any required model files. Run as `python3 solution.py`
and follow the JSON-lines interface. The target is overall RMSE at most
10 microhartree and every stratum's RMSE at most 25 microhartree.

Each system allows 160 query-cost units and at most six virtuals per query.
One persistent process handles the complete suite, with aggregate CPU limit
120 seconds, wall limit 600 seconds, memory limit 2 GiB, and submission limit
128 MiB. No network. Construction time: one hour. CPU and memory accounting
include descendants; their budgets do not reset between systems.
