# Hubbard gap solver

Run the submitted entry point with the requested file interface:

```sh
python3 solver.py REQUEST_JSON PREDICTIONS_JSON
```

The inference artifact consists of `solver.py`, `physics.py`, and `hubbard.so`.
It needs only the Python standard library, NumPy, and the system C++ runtime.
It does not load training data, learned weights, or any participant assets.
No worker threads, child processes, network access, or inference caches are used.
The only file written during inference is the requested predictions JSON.

## Method

The solver performs matrix-free Lanczos calculations on the actual Hubbard
Hamiltonian. A basis is the product of fixed-population up-spin and down-spin
occupation bitstrings. Fermionic hopping signs are computed from the intervening
occupied orbitals. Sparse one-spin hopping operators act on the two axes of the
coefficient matrix; double occupation and onsite potentials act diagonally.
The full many-body Hamiltonian is never materialized.

Gutzwiller-weighted Slater determinants initialize Lanczos. All allowed total-spin
multiplets are considered, so higher-spin ground states in both neutral and
charged sectors are included. Fully polarized endpoints use their analytic
one-particle spectra. Neutral and fixed-Sz-one energies are minimized over the
appropriate nested sets of multiplets. The charge and spin-sector differences
then follow the supplied Hamiltonian convention directly.

Lanczos uses single-precision vectors, double-precision scalar reductions and
tridiagonal eigenvalue calculations, and a convergence check every five steps.
The current cap is 160 iterations with an energy-change tolerance of `1e-8`.
The implementation is deterministic and single-threaded.

## Rebuilding and public checks

The included source builds without third-party C++ dependencies:

```sh
g++ -O3 -march=native -ffast-math -shared -fPIC hubbard.cpp -o hubbard.so
```

`validate.py DATASET_NPZ OUTPUT_PREFIX` checks a labelled public archive and writes
predictions and an accuracy/timing report. `resource_check.py` is a development
wrapper that applies the 25-second CPU and 2-GiB address-space limits and a seccomp
filter denying threads, subprocesses, and network creation before invoking the
solver. It is a smoke test, not a replacement for the trusted evaluator's full
Landlock and seccomp policy. `validation_score.json`, `resource_check.log`, and
`train_check_all.report.json` record public verification results.
