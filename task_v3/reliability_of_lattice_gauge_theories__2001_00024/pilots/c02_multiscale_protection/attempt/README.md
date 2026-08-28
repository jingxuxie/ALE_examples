# Calibrated many-body reliability submission

`solver.py` exposes `solve(case) -> dict` and returns the four numerical blocks
specified by the protocol. It is self-contained at inference time and requires
NumPy and SciPy. `threadpoolctl`, when available, also limits BLAS to one thread.

The command-line interface accepts a JSON file or JSON on standard input:

```sh
python solver.py ../participant/input/example.json
```

## Numerical method

Calibration uses bounded, noise-weighted nonlinear least squares. Each small
experiment is simulated in the exact even-matter-parity Hilbert space, using
dense eigendecomposition or sparse exponential action. All three kinds of
calibration observation enter the fit; additional initial guesses are tried if
the fitted residual is inconsistent with the specified noise.

Prediction evolves the actual supplied open chain, including its dynamical last
link. Small prediction problems use the same exact solver. Larger problems use a
canonical matrix product state with exact global matter-parity symmetry, local
dimension four or six, and a five-stage fourth-order Suzuki composition of
symmetric nearest-neighbor sweeps. Every requested time is reached separately;
there is no time averaging, spatial tiling, or small-chain extrapolation.
The time step accounts for local energy scales and, for linear protection,
neighboring coefficient differences that determine coherent-fault frequencies.

Each Gauss-generator square is kept intact in its associated two-cell
Hamiltonian. Consequently, at zero coherent faults every individual evolution
gate preserves all Gauss generators, and its protection contribution vanishes
separately in the initial gauge sector. The fault-free numerical evolution is
therefore independent of protection strength, without stiff splitting errors
from cancellations between partial expansions of different generator squares.

Schmidt truncation uses a discarded-weight target of `1e-12`, subject to the
available bond dimension. Large, rank-limited blocks use an oversampled,
twice-power-iterated randomized SVD, with exact QR orthogonalization and an exact
SVD fallback for strongly unbalanced parity ranks. The actual discarded norm,
including range-finding error, is accounted for. Initial bond ceilings are 384
for spin one-half and 256 for spin one. A measured-cost controller adjusts these
ceilings to a 3300-second target, leaving margin inside the 3600-second budget.
These are controlled tensor-network approximations, not a claim of exact
long-time evolution at finite bond dimension.

Density, individual squared Gauss generators, and signed connected correlations
are contracted from the same normalized state, including arbitrary distant,
reversed, repeated, and same-site pairs.

## Local validation

```sh
python test_solver.py
SOLVER_TIME_BUDGET=240 python check_chain.py 64 1 8 10 linear
```

`test_solver.py` compares both spin values and both protection families against
the supplied independent dense implementation, checks time-step convergence,
tests noisy parameter recovery near the parameter bounds, and verifies
fault-free Gauss-law conservation and protection independence. It also checks
six- and eight-cell dynamics against sparse exact evolution. `check_chain.py` exercises full-chain
evolution, reports bond dimensions and accumulated discarded norm, and writes
numerical outputs and resource information to a JSON file.

`test_results.txt` records the regression run. `validation.json` records
full-chain bond-dimension comparisons, randomized versus full SVD differences,
and the completed resource stress tests. The associated `chain_*.json` files
contain the numerical predictions used in those comparisons.

Optional diagnostic environment variables are `SOLVER_MAX_BOND`,
`SOLVER_CUTOFF`, `SOLVER_DT`, `SOLVER_TIME_BUDGET`, and `SOLVER_RANDOMIZED=0`.
`SOLVER_ORDER=2` selects second-order sweeps; `SOLVER_ORDER=4` selects a
three-stage fourth-order composition; the default value `5` selects the
five-stage fourth-order composition, not a fifth-order method.
