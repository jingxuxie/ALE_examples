# Numerical contract

The NPZ files contain numeric arrays, never pickle objects.

- `counts`: `(depths, 2**n)` integer final bit-error histograms. Integer column labels use qubit 0 as the least significant bit. Each row is a separate acquisition depth, with its own shot total.
- `depths`: `(depths,)` nonnegative circuit repetition counts, not necessarily uniformly spaced.
- `n`: scalar number of qubits, at most 14.
- `blocks`: binary `(blocks,n)` masks of disjoint qubit groups for the dependence report. A group's event is that at least one bit is nonzero.
- `conditional_queries`: binary `(queries,3,n)` masks giving disjoint, nonempty X and Y and possibly empty Z. Each selected set is a full categorical bit-vector, NOT an OR event.
- `parents`: binary `(n,n)` DAG adjacency; `parents[child,parent]=1`.

The effective error distribution is over observed bit errors after local averaging, not an unaveraged `4**n` Pauli distribution. A parity mode of repeated idealized data has an unknown multiplicative SPAM amplitude and a per-cycle geometric decay. Records are finite experimental observations: late, nearly vanished modes need not follow a clean exponential. The desired one-cycle channel excludes the SPAM amplitude. Do not treat depth-zero observations as a noiseless calibration or infer a single common rate for all modes.

Required output arrays:

- `probabilities`: `(2**n,)`, finite, nonnegative and normalized.
- `correlations`: `(blocks,blocks)`, Pearson correlation of the group events under the recovered distribution. Diagonals are 1 unless variance vanishes, in which case use 0.
- `conditional_information`: `(queries,)`, conditional mutual information I(X;Y|Z) in natural logarithms.
- `spatial_jsd`: scalar Jensen–Shannon **distance**, using base-two logarithms, between the recovered distribution and `q(x)=product_i p(x_i|x_parents_i)`. This q is the normalized DAG model with conditionals obtained from the recovered distribution. For a zero-probability parent configuration use the fair binary conditional. No labels are supplied for the example.

Hidden data use the same contract. Distribution error is measured away from the identity spike, so returning nearly all identity receives little credit. Diagnostics are scored independently; computing them consistently from an inaccurate channel does not guarantee a high score. Submit reusable computation, not an output for the example alone.
