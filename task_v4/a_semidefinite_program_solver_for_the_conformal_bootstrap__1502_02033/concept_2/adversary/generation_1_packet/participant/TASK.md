# Falsify a continuum polynomial-matrix screen

Construct a small, well-scaled rational symmetric matrix polynomial that a strong
floating numerical screen accepts on **every point of [0,1]**, even though an
interior rational point and a collective rational direction prove it negative.
The screen's acceptance is a heuristic assertion, not a verified SDP certificate.

## Assets and interface

- `input/README.md` specifies the complete data contract and fixed thresholds.
- `workspace/guard.py` is the public, frozen target: independent meshes,
  determinant stationary/root candidates, adaptive eigenvalue minimization,
  and frozen-Rayleigh stationary searches in three profiles.
- `workspace/baseline_search.py` is a runnable coupled-spectral-branch search.
- `input/example_rejected.json` is admissible negative evidence the guard detects,
  not a solution.

The baseline and guard accept explicit output/input paths:

```sh
python <participant>/baseline/search.py --output <output>/witness.json --trials 4
python <participant>/workspace/guard.py <output>/witness.json
```

Write **`witness.json` in your writable output directory**. Participant assets
are read-only; put all experiments and modified code in your output directory.
You may experiment with the public guard, but grading uses an immutable private copy.
The evaluator reads JSON data only; it never executes your programs. It checks
all algebraic constraints and the normalized Rayleigh quotient with exact
rational arithmetic.

## Objective and resources

Find exact negativity of at least `1e-7`, while every screening profile accepts.
The constraints require positive one- and two-coordinate principal tests at the
witness and noncommuting matrix values: a scalar quadratic hidden in a constant
eigenbasis is not eligible.

You have one hour. Use Python with NumPy/SciPy; no network, external services, SDPB installation, or
GPU is needed. Keep BLAS single-threaded. A trial has degree at most 24 and four
matrix coordinates. Baseline search time is yours to allocate; grading a single
bounded data file takes only a small CPU budget. A known successful witness is
not supplied and existence against this particular screen is not asserted.

Scores reward admissible exact counterexamples that fool more profiles, with
full success only when all profiles accept. Runtime is secondary and contributes
only to successful witnesses. Admissibility alone is not success.
