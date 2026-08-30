# Compact equilibrium proposals

## Run

```bash
python solve.py INSTANCE.json MODEL.json
```

`solve.py` is self-contained and requires only Python, NumPy, and SciPy. It does
not import the supplied workspace, read training examples, use a GPU, or access
the network. The output contains exactly `mixing`, `weights`, `biases`, and
`orders`, with at most eight normalized triangular logistic components.

## Method

1. Enumerate the finite Ising target exactly, using the couplings and fields as
   already temperature-scaled parameters. Normalize with log-sum-exp.
2. Select three conditioning sites using exact conditional covariances, with
   alternative graph cutsets for sparse interactions. Their eight assignments
   partition all configurations; component weights are the exact partition
   probabilities, not frequencies estimated from samples.
3. For each partition, fit every autoregressive Bernoulli conditional by exact,
   weighted logistic regression. Marginalizing suffix spins avoids Monte Carlo
   noise. The last conditional starts from analytic Ising logits. Compare
   elimination-based, covariance-based, and deterministic random orderings.
4. Select models with exact reverse KL and population importance-weight
   diagnostics. Refine the selected models by preconditioned L-BFGS on
   `KL(q||p) + 0.03 KL(p||q) + 0.002 (1/ESS - 1)`, using enumerated analytic
   gradients. The last term explicitly penalizes undercovered target tails.

The conditioning logits are finite (`+55` or `-55`). Their total leakage is
below `4e-24` per component. No hard zeros are introduced into the returned
distribution. All conditional parameter L1 norms are bounded by 59, below the
interface limit of 60. The serialized model contains only the requested small
parameter arrays; enumeration tables are not part of the artifact.

The implementation uses one BLAS thread and an internal deadline near 105
seconds, leaving headroom within the 120-second invocation limit. It retains
the best completed model throughout optional search and refinement. Damped
Newton updates and an accepted-step line search protect fitting from saturated
low-temperature initializations.

## Validation

```bash
python -m unittest -v test_solver
python validate.py --input-dir /path/to/public/input --stress
```

The eight unit tests cover exact six-spin reconstruction, independent spins,
weighted logistic projection, saturated initialization, finite-difference
gradient checking, the partition-based ESS calculation, finite bounded
parameters, and valid output after an exhausted fitting budget.

`validate.py` runs fresh solver subprocesses with a 118-second timeout, validates
every artifact constraint, and computes reverse KL, ESS, and normalization over
the complete state space. Its optional deterministic stress suite includes all
three interaction families, 18/19/20 spins, zero and nonzero fields, and both
moderate and substantially colder couplings. Results are written to
`validation_results.json`.

### Measured results

The final solver was tested in 15 fresh CLI processes: the three public examples
and twelve generated stress cases. All artifact and normalization checks passed.

| Public family | Reverse KL | Supplied baseline KL | ESS fraction |
| --- | ---: | ---: | ---: |
| Dense disordered | 0.00332724 | 0.04853406 | 0.980362 |
| Associative memory | 0.00113778 | 0.01539167 | 0.997600 |
| Frustrated lattice | 0.00885796 | 0.03194242 | 0.979503 |

Public mean reverse KL is **0.00444099**, an **86.10% reduction** from the
supplied baseline's 0.03195605. Across all 15 final cases, maximum reverse KL
was 0.00896258 and minimum population ESS was 0.974112. The longest measured
solver invocation took 13.80 seconds; peak child-process RSS was 786,784 KiB
(about 0.75 GiB), and the largest artifact was 33,773 bytes. These timings are
measurements on the development host, not assumptions made by the solver.
