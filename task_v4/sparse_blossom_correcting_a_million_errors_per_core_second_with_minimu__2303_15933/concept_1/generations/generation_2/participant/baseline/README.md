# Frozen promoted baseline

`submission.py`, `decoder.cpp`, `decoder.so`, and `Makefile` are code-only,
byte-identical copies of the confirmed preceding champion. The native binary
is unchanged. Import `baseline.submission`, not the raw ctypes library `decoder`.

The decoder uses layered damped sum-product belief propagation, reliability-
ordered binary elimination, a local low-order search over free variables, and a
deterministic channel-perturbation ensemble. Candidate likelihoods are summed by
logical label. A converged unperturbed BP solution has an early return. Default
settings are 40 BP iterations, order parameter 40, and 8 ensemble trials for
one-round cases or 2 for memory cases.

This is a baseline, not a restriction on your method. Native source is provided
so implementation bottlenecks and inference choices can both be improved. The
frozen objective does not award speed alone or a prescribed algorithm.
