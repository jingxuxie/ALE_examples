# Fixed physical model and artifact contract

This is a new quantitative robustness conjecture seeded by arXiv:2112.09853,
not a claim that the original paper asserted these numerical bounds.

Four qubits have ring connectivity. SPAM, outer local-Clifford randomization,
and interleaved independent Pauli randomization are perfect. Noise is a
time-independent stochastic Pauli channel applied after each ideal layer;
noise cannot depend on mirror position, depth, or any random Pauli frame.
Unmentioned qubits are idle and perfect.

There are 32 ideal layer classes. Each of 24 one-qubit classes has probability
1/40. Each of eight directed CNOT classes has probability 2/40. The one-qubit
classes are indexed first by site 0,1,2,3 and then by the following six images
of `(X,Z,Y)`, using digits `I=0, X=1, Z=2, Y=3`:

```
(1,2,3), (1,3,2), (2,1,3), (2,3,1), (3,1,2), (3,2,1)
```

Each class includes all four signed Clifford variants uniformly, with the
same error channel. Conjugation of stochastic Pauli noise ignores signs.
The CNOT class order `(control,target)` is:

```
(0,1), (0,3), (1,2), (1,0), (2,3), (2,1), (3,0), (3,2)
```

The ensemble is inverse symmetric. Its ideal nonidentity-Pauli mixing spectral
gap is approximately 0.0698264; the sampler is fixed, not a submission variable.

## Noise allocation

The JSON object has exactly two keys. `single` has shape `[4,6,3]`, error columns
`X,Z,Y` on the selected site. `cx` has shape `[8,15]`; column `index-1`, with
`index=1,...,15`, applies Pauli digits `(index % 4, index // 4)` on the ordered
control and target. Entries are JSON integers, not floats or booleans.

For row L, a listed nonidentity Pauli Q occurs with probability `count_L(Q)/3000`.
The identity occurs with probability 0.98. Thus every row sums to 60.
One-qubit counts lie in `[2,42]`; CNOT counts lie in `[1,21]`.

Embed counts into the full four-qubit Pauli alphabet, zero outside a row's
listed support. Let `h_L` be 1 for one-qubit rows and 2 for CNOT rows.
For every weight-one global Pauli, require `sum_L h_L count_L(Q) = 152`.
For every weight-two global Pauli on a ring edge, require the same sum to be 16.
All other global Pauli counts vanish. In addition require the exact integer
inverse-pair overlap:

```
sum_L h_L sum_Q count_inverse(L)(Q) * count_L(L Q inverse(L)) = 32640
```

The average error channel is also calibrated separately within each native
family. Require these exact **unweighted** marginal sums for every global
nonidentity Pauli Q:

- Over the 24 one-qubit classes: 120 for a weight-one Pauli, zero otherwise.
- Over the eight CNOT classes: 16 for a weight-one Pauli, 8 for a weight-two
  Pauli on a ring edge, zero otherwise.

The globally weighted marginal condition follows from these family conditions
but is also checked explicitly. The noise within individual gate classes need
not be isotropic; only the stated family averages are fixed.

The calibration also resolves which native-gate family generated the inverse
pair. The following two unweighted conditional overlap sums must match exactly:

```
sum_(L one-qubit) sum_Q count_inverse(L)(Q) * count_L(L Q inverse(L)) = 28800
sum_(L CNOT)      sum_Q count_inverse(L)(Q) * count_L(L Q inverse(L)) = 1920
```

The first sum contains 24 equally weighted classes, the second eight. These
are equivalent to preserving depth-two mirror polarization within each native
gate family, not merely after mixing their observations. The overall overlap
condition follows from these two equalities but is also checked explicitly.
Both native-family average channels and both native-family pair calibrations
therefore match the uniform baseline. If the same conditional noise channels
were used with a different CNOT sampling probability, these calibrations would
still match: each combined calibration is the corresponding weighted sum of
its two family calibrations. This does not assert invariance of the fitted
long-depth error rate. The actual sampler and all scoring depths remain fixed.
Layer-infidelity covariance is identically zero.

## Observations and acceptance

A benchmark-depth `2m` mirror samples `m` independent ideal layers, followed by
their inverses in reverse order, with the stated stochastic noise at all layers.
The effective polarization is the averaged normalized trace of the resulting
Pauli error channel. `workspace/model.py` provides an exact Pauli-transfer
calculation, not a Monte Carlo estimate. All 129 even depths from 0 to 256 are
used, with no fit weights or additive offset.

The least-squares fit is `S_d = A exp(-t*d)`. For each t, A is the exact
least-squares amplitude. The checker scans 4097 t values in `[0.005,0.04]`,
refines every local minimum with bounded scalar minimization, and compares
endpoints. It reports `r = (255/256)*(1-exp(-t))` and bias `1-r/0.02`.

Acceptance requires bias >= 0.0235, `max_d abs(S_d-A exp(-t*d)) <= 0.004`,
and `S_256 >= 0.005`, together with all exact integer constraints. Floating
metric comparisons allow 1e-10 numerical slack; integer equalities allow none.
The public checker and official checker use identical physical semantics.

Uniform baseline noise has all one-qubit counts 20 and all CNOT counts 4.
No implementation passes merely by submitting this calibration baseline.
