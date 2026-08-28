# Interface and statistical target

## Invocation

`python3 solve.py --input <json> --output <json>`

Read one UTF-8 JSON document and write one finite-valued JSON document to the specified output path. Do not depend on the current directory, input filename, internet access, or persistent state across calls. Stdout is not the answer. The runtime allowance is 120 wall-clock seconds and 2 GiB per case.

## Input

The object has `schema_version: 1`, `block_sizes`, `expressions`, and `replicas`.

- `block_sizes`: distinct positive integers, in the requested output order.
- `replicas`: a list of independent streams. Each has `signs` (length N, entries +1 or -1) and `measurements` (N rows by D columns). Row order is Monte Carlo time. All replicas have the same D but can have different lengths. Measurements are unsigned channel values, not already multiplied by signs. They may themselves be negative.
- `expressions`: an ordered list of scalar expression trees describing functions of reweighted channel means. `{"moment": 0}` refers to column zero; `{"constant": 2.0}` is a scalar constant. Other nodes have `op` and `args`. Binary operators are `add`, `sub`, `mul`, `div`; unary operators are `log`, `sqrt`. There is no pointwise transformation of measurements implied by an expression.

Inputs have 2–5 replicas, 2–8 measurement columns, 2–6 expressions, up to 120,000 total rows, and up to four blocking scales. Every replica has at least three nonempty batches at each requested scale. The full and all delete-one-batch expression evaluations are finite and in-domain; their average-sign denominators are nonzero. No labels or reference answers are supplied.

## Exact estimand

For each measurement form the aligned joint vector `y = (sign, sign*x[0], ..., sign*x[D-1])`. For a joint mean `mu`, let `F(mu)` evaluate every expression using `moment[j] = mu[j+1]/mu[0]`. A ratio of means is not a mean of ratios.

For each requested block size, partition each replica separately into consecutive, nonoverlapping blocks. Keep its final partial block with its actual positive count. Never construct a block across two replicas. For the pooled analysis, collect these blocks from all replicas; do not average replica estimates equally. For each per-replica analysis, use only that replica's blocks.

The requested uncertainty is the finite-sample weighted delete-one-batch jackknife convention, not the variance of raw measurements, not a delta-method approximation, and not an additional extrapolation to infinite block size. The same convention applies to pooled and individual-replica analyses:

For block b, let n_b be its count and S_b its sum of joint vectors. Set N = sum_b n_b, S = sum_b S_b, and w_b = n_b/N. Let theta = F(S/N), theta_without_b = F((S-S_b)/(N-n_b)), and

`p_b = [N*theta - (N-n_b)*theta_without_b] / n_b`.

Return the bias-corrected vector `theta_J = sum_b w_b*p_b`. With q = sum_b w_b^2, return the **covariance of that estimated mean vector**

`C_J = q/(1-q) * sum_b w_b * (p_b-theta_J)(p_b-theta_J)^T`.

This convention includes count weighting for unequal final blocks. For equal block counts it reduces to the ordinary delete-one-block jackknife. The requested scales deliberately expose the effect of temporal correlations; do not return an iid covariance at every scale. A finite-sample block estimate need not equal an unknown infinite-run covariance.

## Output

Return `{"schema_version": 1, "analyses": [...]}`. Each analysis, in input order, has:

- `block_size`: the corresponding requested integer.
- `pooled`: `{"mean": [...], "covariance": [[...], ...]}` for all replicas combined as described.
- `replicas`: a list of objects with the same `mean` and `covariance` fields, in input replica order.

Each mean has one entry per expression. Each covariance is a square matrix in the same expression order, symmetric and positive semidefinite up to roundoff. Standard deviations, correlation matrices, covariance of unnormalized numerators, or only diagonal entries are not substitutes. All numeric entries must be finite JSON numbers. Missing analyses, wrong shapes, nonfinite values, and malformed output receive zero for the case.

## Accuracy

Means, diagonal covariance scales, off-diagonal correlation structure, and replica mean/covariance outputs are checked separately. Scores are continuous against a stored strong calculation, calibrated to the supplied weak baseline. A nonzero finite error is not assigned a perfect score. The case score cannot exceed its hard covariance components or its hardest requested blocking scale. No hidden estimator-selection rule is used.
