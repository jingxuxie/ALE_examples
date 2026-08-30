# Numerical and JSON contract (version 1)

## Interface
From the participant directory, run `python output/solve.py < input/sample_01.json`. A fresh process receives
one JSON object on stdin and must print exactly one JSON object on stdout; send
diagnostics to stderr. No arguments, network, persistent state, or hidden files.

Input `version: 1` contains `blocks` and `rhs`. Each block has a unique `id`,
`kind` (`interval` or `point`), decimal-string `origin` and positive `scale`,
`matrix`, and `moments`. The local coordinate is
`t = (x-origin)/scale`. An interval is **closed**, `-1 <= t <= 1`; a point
has only `t=0`. A coefficient array `[[a0,b0,c0], [a1,b1,c1], ...]` means

```
H(t) = sum_k [[ak,bk],[bk,ck]] T_k(t),
T_0=1, T_1=t, T_(k+1)=2*t*T_k-T_(k-1).
```

`matrix` specifies the real symmetric functional matrix M. All its coefficients
are **exact terminating decimal rationals**, not rounded double-precision fits.
M is PSD everywhere on its permitted domain. Every zero is isolated and has
nullity one. Full-rank point blocks and very small positive minima are NOT atoms.
There are no identically singular blocks. Interior contacts can have higher even
order; endpoints need not. `moments[r]` specifies H for global equation r.
The decimal-string `rhs[r]` is supplied to 240 significant digits:

```
rhs[r] = sum_atoms weight * trace(H_block,r(t) * projector).
```

The trace of two packed symmetric matrices is `a*p00 + 2*b*p01 + c*p11`.
Every zero has strictly positive weight; the moment design has full column rank
at the true atoms. Weights are not determined by M alone. Their scale is fixed
by these equations, not by a determinant derivative or arbitrary normalization.

Output, in any order:

```json
{"version":1,"atoms":[{"block":"b0","x":"0.25","projector":["0.5","0.5","0.5"],"weight":"2.0"}]}
```

Return every atom exactly once. The packed projector is `u*u^T`, `||u||=1`;
thus the sign of u is immaterial, and the reduced OPE vector is `sqrt(weight)*u`.
Prefer decimal strings for all numbers: double-precision output cannot represent
some physical-coordinate separations. Do not output factors, certificates, or
additional keys. An empty `atoms` list is valid syntax, not a successful solution.

## Fixed objective
Matching is one-to-one within each block. In local coordinates a location must
be within `min(2e-8, nearest_same_block_atom_gap/40)` of its true value (the gap
term is omitted for a singleton). Direction credit additionally requires
projector Frobenius error <= `2e-6` and
`||M(t) P||_F / ||M(t)||_F <= 2e-8`. Weight credit additionally requires
relative error <= `2e-4`. Projectors must be PSD, unit-trace rank-one within the
validation tolerances (trace `1e-6`, idempotence `5e-6`, minimum eigenvalue `-1e-8`).
Out-of-domain coordinates beyond `2e-14` in t are invalid.

Each case scores `0.30*F_location + 0.30*F_direction + 0.30*F_weight + 0.10*C`.
Each F is `2*credited_atoms/(true_count+returned_count)`; extras and duplicates
therefore hurt. C is one only when the maximum global moment residual, divided
rowwise by `max(1,abs(rhs[r]))`, is <= `1e-8`. No atoms gives C=0.

The deterministic hidden suite has six equally weighted families: separated,
near-coincident, multiscale, boundary/isolated-point, rotating-null, and coupled
high-order contacts. **Pass: core mean >= 0.90 AND worst-family mean >= 0.80,
no protocol failures, <= 240 seconds total participant wall time.** Limit:
30 seconds per case, 1 GiB address space, one numerical thread, 1 MiB stdout,
256 returned atoms. Missing fields, unknown blocks, malformed/nonfinite values,
nonphysical projectors, crashes, and timeouts fail that case and prevent passing.
Numbers must have <= 2048 characters and magnitude <= `1e1000`.
Ranking is core, then worst family, then lower runtime; runtime is not accuracy.

## Input bounds
Python 3.10, NumPy 1.21.5, SciPy 1.8.0, mpmath 1.3.0 and the standard library
are available; no cvxpy, external services, or additional packages are required.
Matrices have degree <= 64, at most 5 blocks and 32 atoms, and 40 moment rows
of degree <= 16. Local gaps can approach `1e-10`; weights span `1e-12` to `1e11`.
Coordinate offsets, matrix anisotropy, close complex roots of positive factors,
and moving null spaces make indiscriminate double conversion unsafe.
`../evaluator/`, its hidden data, attempts and champion management
are organizer-only and must not be used by a submission.
