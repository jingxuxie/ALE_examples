# Data and numerical conventions

## Material
There are `height=8`, `columns=12` spins, numbered `column*8+row` (column-major).
Open boundaries apply in both directions. Spins are -1 or +1. Thirty-two spins
are always hidden; the same 64 visible indices, sorted increasingly, are measured
in every configuration. Hidden-hidden edges exist. The mask and graph are not
inference targets.

The distribution is

`p(s | beta,u) = exp(beta*(sum_edges J[e]*s[a]*s[b] + sum_sites (h[i]+u[i])*s[i])) / Z`.

Thus `u` is a physical field, multiplied by beta just like `J` and `h`.
The known sign of every coupling is in `edge_signs`, aligned with `edges`.
Coupling magnitudes and all fields are unknown; the bounds and independent
uniform generating prior are declared in `parameter_prior`. The known signs
are a manufacturing prior, not estimated correlations. No other parameter
sharing, translation invariance, hidden-spin independence, or zero-field
assumption is warranted.

Edges are ordered: all within-column vertical edges, with column outermost and
row innermost; then all between-column horizontal edges in the same order.
`transfer.model_from_edges(spec, couplings, fields)` accepts this ordering.

## Training archive
Load using `np.load('input/train.npz', allow_pickle=False)`.
`betas`: float64 `(2,)`, values `[0.65,1.0]`.
`visible_spins`: int8 `(2,8192,64)`, values -1/+1. The final axis follows
`visible_indices`. Configurations and the two conditions are sampled independently
by exact backward transfer sampling; there is no burn-in or MCMC time correlation.
All training fields `u` are zero. Sampling is exact finite-model sampling up to
floating-point precision, not sampling from a neural surrogate.

## Queries
JSON list of 24 objects, ordered by family and then local index. Keys:
`id`, `family`, `beta`, `readout`, `field_indices`, `field_values`.
The readout is an ordered list of six visible spin IDs in one column. An omitted
field is zero; add each listed field to the unknown background field. All field
sites are visible and, in this release, lie in that query's readout.

Interpolation uses beta 0.85; cooling alternates 1.15 and 1.30 with zero added
field. Field queries use beta 1.15 or 1.30 and nonzero fields; there is no
duplicate experiment between families. Query parameters are public, labels hidden.

Outcome `code` in `[0,63]` means
`readout[k] = 2*((code >> k) & 1)-1` for `k=0,...,5`.
Readout position zero is the least significant bit. Probabilities marginalize
over every other visible and hidden spin; they do not condition on a training
configuration.

## Submission archive
Exactly two ZIP members: `probabilities.npy` and `query_ids.npy`. Create with
`np.savez` or `np.savez_compressed`. Arrays must be C-contiguous:
`probabilities`: little-endian float64 (`<f8`), shape `(24,64)`;
`query_ids`: little-endian Unicode (`<U24`), shape `(24,)`, matching all IDs exactly.
No pickles, object arrays, extra arrays, duplicate members, encryption, or
symlink artifacts. Only NPY versions 1/2 and stored/deflated ZIP are accepted.
Every probability must be strictly positive and <=1; row sums must differ from
one by at most `1e-10`. Accepted rows are renormalized within that tolerance.

Forward KL is `sum_code p_true*log(p_true/p_submitted)` in natural units.
Total variation is `0.5*sum_code abs(p_true-p_submitted)`. Average KL equally
over the 24 queries; each family's mean equally averages its eight queries.
The maximum TV is over all queries. All three published inclusive limits apply.
The hidden scorer reports deterministic finite-instance metrics, not a
Monte Carlo estimate. Full scores are organizer-only during a sealed attempt.

## Simulator
`StripIsing(vertical, horizontal, fields)` expects shapes `(12,7)`, `(11,8)`,
`(12,8)`. `log_partition`, `column_marginals`, `joint`, and `sample` accept beta
and optional `field_delta` of shape `(12,8)`. `sample` returns full synthetic
configurations only under parameters supplied by its caller.
`log_partition` and `column_marginals` also accept evidence of shape `(12,8)`:
0 means unobserved, +/-1 clamps a spin. A clamped partition function sums only
compatible states, so subtracting the unclamped log partition gives a visible
configuration's log probability. The helper is not an inference algorithm.
