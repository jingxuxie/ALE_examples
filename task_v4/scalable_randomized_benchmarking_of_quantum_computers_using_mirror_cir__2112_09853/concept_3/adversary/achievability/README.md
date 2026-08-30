# Bounded private achievability search

This directory is private and is not part of the participant package. The
frozen participant and evaluator are read-only inputs. No fresh-attempt files
are read. Existing author-created ladder and bridge circuits are reused.

Run from the concept directory with bytecode writes and BLAS threads disabled:

```sh
PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 python -B adversary/achievability/search.py --seconds 1200 --workers 4
```

At most four single-threaded search workers run. They stop on the first exact
feasible candidate or the wall-time deadline. After workers exit, the original
official evaluator checks a static full-three-family artifact. Outputs are
confined to this directory and `champions/private_achievability*.json`.

Each run saves input snapshots, seeds and SHA-256 commitments before searching,
configuration/source hashes, progress, per-worker results, CPU/wall time, the
best candidate, and official evaluation results. Reproduce from a saved config:

```sh
PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 python -B adversary/achievability/search.py --seconds 1200 --workers 4 --replay adversary/achievability/RUN_DIRECTORY/config.json
```

Random streams are reproducible; the wall-clock cutoff and cross-worker early
stop may change the number of evaluations reached on a different machine.
The grid inverse warm start removes only endpoint local Cliffords and uses
unsigned inverse representatives. Its swapped weight distributions are checked
before any search. This is a support certificate, not a phase/unitary identity
claim for the normalized inverse artifact.
