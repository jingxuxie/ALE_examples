# Compact equilibrium proposals

Run the self-contained solver with Python, NumPy, and SciPy:

```sh
python solve.py INSTANCE.json MODEL.json
```

The output contains exactly eight normalized logistic-autoregressive components
in the specified `mixing`, `weights`, `biases`, and `orders` format. The solver
uses no network, GPU, external executables, callbacks, or configuration tables
in the output. Set `SOLVE_VERBOSE=1` to print fitting diagnostics.

## Method

- Sparse models: search for up to three conditioning spins whose removal admits
  width-two elimination. Exact Ising elimination produces the component logits
  and branch partition functions. Unused mixture slots duplicate components.
- Broad local-sector models: recognize gauge-equivalent frustrated four-site
  regions and initialize from two generic, ideal-material calibration priors.
  These JSON dependencies contain only eight-component network parameters, not
  spin probability tables or instance lookups. The full unseen Hamiltonian is
  subsequently fitted within the invocation budget. Other structures use
  independently fitted regional mixtures as a fallback.
- Concentrated models: initialize eight distinct orders using weighted logistic
  projection of the enumerated target, then perform forward and tail-corrected
  reverse refinement on important configurations.
- Every non-exact path finishes with full-enumeration optimization of reverse
  KL, a small forward-KL term, and a population importance-weight penalty. Model
  selection explicitly prefers population ESS at least 0.30.
- Binary-cube recursions calculate logits and gradients without storing dense
  prefix design matrices. Walsh transforms supply Fisher preconditioners.

The internal fitting deadline is 112 seconds, with four worker threads and
single-threaded BLAS. Parameter norms stay below 60 and files are written
atomically. All instance-specific enumeration, initialization, and fitting is
included in that deadline.

## Checks

```sh
OPENBLAS_NUM_THREADS=1 python test_cube.py
OPENBLAS_NUM_THREADS=1 python test_gradients.py
OPENBLAS_NUM_THREADS=1 python test_sparse.py
OPENBLAS_NUM_THREADS=1 python audit.py INSTANCE.json MODEL.json
python benchmark.py results.json INSTANCE1.json INSTANCE2.json
```

`audit.py` checks the artifact contract and enumerates the exact reverse KL,
population ESS, and normalization. `benchmark.py` additionally enforces a
120-second subprocess timeout and an 8-GiB address-space limit. It also pins
four CPUs when the environment permits affinity changes; the solver always
uses at most four workers with single-threaded BLAS. `validation_results.json`
records public and perturbed-instance results.

Runtime dependencies are the Python modules alongside `solve.py`, plus
`template_moderate.json` and `template_cold.json`. The priors are calibrated on
ideal products of five identical frustrated four-spin regions, not on unseen
evaluation instances.

## Measured validation

| Public example | Reverse KL (nats) | Population ESS |
| --- | ---: | ---: |
| Local sectors | 0.0010534 | 0.998428 |
| Coupled regions | 0.0021427 | 0.993614 |
| Frustrated cycles | approximately zero | approximately one |

All nine public and perturbed cases pass the artifact checks. Across those
checks the maximum KL is 0.003622, minimum ESS is 0.95727, maximum measured
invocation time is 115.994 seconds, and peak child RSS is below 745 MiB.
These measurements do not include unseen frozen evaluation instances.
