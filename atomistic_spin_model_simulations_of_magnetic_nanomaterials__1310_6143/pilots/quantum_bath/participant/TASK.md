# Resonant spin-bath dynamics

Replace the classical relaxation baseline with a reliable finite-memory thermal
spin solver. Reproduce the bath covariance, spatially resolved magnetization,
and restart state for the supplied magnetic systems, including resonant baths,
low-temperature statistics, and competing magnetic sublattices.

Submit a self-contained `solve.py` in the attempt directory, invoked as
`python solve.py CASE.json OUTPUT.npz`. The input contract is in
`input/FORMAT.md`; `workspace/common.py` supplies geometry and deterministic
initialization. The classical baseline is not a specification of the target
physics. Do not change the input files.

Evaluation includes all three physical output groups, unseen material regimes,
systems up to 46,656 spins, and measured resource use. A case has a 180-second
execution allowance and a 1.5-GiB address-space limit, with one CPU thread.
Compilation time counts. NumPy, SciPy, Numba, and a C++ compiler are available.
