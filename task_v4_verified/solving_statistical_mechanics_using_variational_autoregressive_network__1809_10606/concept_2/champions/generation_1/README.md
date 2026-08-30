# Full-support false-convergence witness

The submission is `witness.json`. It passes all structural constraints and all
seven numerical gates under two independently implemented exhaustive
enumerations of all 65,536 configurations. No probabilities are clipped,
discarded, floored, or renormalized.

## Results

The standalone, standard-library verifier reports:

| Metric | Measured | Required |
| --- | ---: | ---: |
| Entropy | 3.47707143449790 | >= 3 |
| Reverse KL | 2.09108532537111 | >= 0.4 |
| Dimensionless reward variance | 0.0169944619598756 | <= 0.05 |
| Exact gradient infinity norm | 0.000484874806609972 | <= 0.003 |
| Dimensionless energy error per spin | 0.00470204545174108 | <= 0.02 |
| Target sector mass | 0.458455457881630 | >= 0.35 |
| Proposal sector mass | 0.0000252509211633720 | <= 0.001 |

All seven clipped gate scores, and their minimum, are 1. These are local
verification results, not a claim to have run the hidden evaluator.

Additional checks:

- There are 12 frustrated plaquettes, and beta is 1.6.
- Every nonzero weight is 9.2, strictly below ln(9999).
- The minimum conditional probability is 0.000101029193907773.
- The minimum enumerated state probability is 3.49756494950746e-46.
- The proposal normalization is 0.9999999999999999.
- The maximum enumerated spin-flip symmetry error is zero.
- The JSON is a regular UTF-8 file with exactly the seven required keys.

## Construction

Physical spin 5 is a fair root spin. The other eleven backbone spins each copy
that root independently with probability sigmoid(9.2). Physical spins
4, 6, 13, and 15 are independent fair spins, placed last in the autoregressive
order. Thus the model has only eleven nonzero weights, all in the first column
below the diagonal. Its logits have no biases.

When all eleven backbone copies agree with the root, the model is uniform on
32 configurations. All 32 have ground-state energy -16 for the submitted
bonds. This event has proposal probability 0.9988892400762924. The entropy has
the independent analytic expression

    H(q) = 5 ln(2) + 11 h(epsilon),
    epsilon = sigmoid(-9.2),

where h is binary entropy in nats. The finite logistic weights retain full
support outside this ground-state subset.

The submitted antipodal radius-4 sector contains none of those 32 configurations
but contains 118 of the lattice's 256 ground states. Consequently, the exact
target assigns it approximately 45.85% probability, whereas the proposal assigns
it approximately 0.002525%. Small reward variance and small ambient-coordinate
gradients coexist with reverse KL greater than 2 nats and a severely
underrepresented equilibrium sector.

## Reproduce and verify

From this output directory:

```sh
python -B construct.py
python -B verify.py --output verification.json
```

`verify.py` uses only the Python standard library. It validates the schema and
structural bounds, then enumerates every state and all 120 gradient coordinates.
`verification.json` records its complete passing result.

An independent NumPy/SciPy implementation is also included:

```sh
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python -B diagnostics.py witness.json
```

Its result is saved in `metrics.json`. The two implementations agree within
3e-13 on all seven metrics. Additional checks confirmed the 32-state ground
subset, its analytic probability and entropy, and six ambient gradient
coordinates against central finite differences (maximum discrepancy below
1e-9 with step 1e-4).

The discovery search source and screening results are retained as supporting
working artifacts. They are not required to load or evaluate `witness.json`.
