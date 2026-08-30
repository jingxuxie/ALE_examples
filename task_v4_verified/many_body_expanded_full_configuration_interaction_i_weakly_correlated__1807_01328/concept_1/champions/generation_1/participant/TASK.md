# Adaptive correlation-energy experiments

Develop an autonomous acquisition policy for recovering a weakly correlated
paired-electron ground-state energy from restricted active-space experiments.
This model-system benchmark is seeded by virtual-orbital MBE-FCI; it is not an
ab initio molecular benchmark.

You receive a simulator, labeled practice systems, exact one/two-virtual CAS
energies, inexpensive descriptors, and a runnable acquisition baseline. Hidden
systems come from the six documented physical-model families.

Submit `solution.py` and any model files in your output directory. It must run
as `python3 solution.py` and speak the JSON-lines interface in
`workspace/INTERFACE.md`. At evaluation it sees only observations, never hidden
Hamiltonians, full-space energies, or hidden identifiers.

Recover the full eight-virtual correlation energy with overall RMSE at most
10 microhartree and every family's RMSE at most 25 microhartree. Each system has
160 query-cost units; queried spaces contain at most six virtual orbitals.
The complete hidden run allows 120 CPU seconds, 180 wall seconds, 2 GiB memory,
and a 128 MiB submission. No network. Construction time: one hour.

Scoring measures energy accuracy, worst-family accuracy, query cost, and runtime.
See `workspace/INTERFACE.md` for executable details and practice commands.
