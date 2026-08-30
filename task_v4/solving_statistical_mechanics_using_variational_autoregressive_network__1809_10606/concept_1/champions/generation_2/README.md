# Equilibrium proposal solver

Run:

```sh
python solve.py INSTANCE.json MODEL.json
```

The runtime dependencies are `regional.py`, `optimization.py`, NumPy, and
SciPy. All fitting is performed afresh from the supplied instance. No example
models, validation data, network access, GPU, or external files are needed.

## Method

1. Enumerate the target distribution exactly and detect its strongly coupled
   regions. Fit two overlapping, differently ordered logistic autoregressive
   distributions to each exact regional marginal.
2. Combine regional components using a balanced binary design with eight rows.
   For three regions this is the complete product; for four regions all
   three-region latent marginals are independent, and for five regions all
   two-region latent marginals are independent. An overlap penalty prevents
   the initialization from becoming a collection of hard, poorly covered
   partitions.
3. Optimize the complete eight-component mixture against the exact 20-spin
   target. This stage fits **all** causally permitted weights, including
   inter-region weights, as well as mixture probabilities. The loss is
   reverse KL plus 0.05 times forward KL plus 0.002 times the excess population
   chi-square factor. The last term directly discourages low population ESS.
4. Use regularized conditional Fisher preconditioning and analytic
   reverse-mode gradients through the prefix probability trees. Project each
   conditional parameter vector to an L1 norm of at most 59, below the
   interface's bound of 60.

The resulting JSON is solely the required normalized mixture of eight
autoregressive networks. Enumeration tables and regional bookkeeping are
training aids and are not part of the artifact.

## Resource handling

BLAS runs with one thread, and component evaluations use four worker threads.
The solver stops fitting at an internal wall-clock deadline of 105 seconds,
retains the best finite objective with ESS at least 0.30 when such an iterate
is available, and writes the final model
atomically. It also writes a valid initialization before the joint fit.
Set `SOLVE_VERBOSE=1` to emit fitting diagnostics to stderr.

## Validation

`check.py` validates artifact shapes, normalization, causality, parameter
bounds, and file size, then computes reverse KL and population ESS by complete
enumeration. Its results have been independently cross-checked against the
provided `workspace/van.py` utility. Finite-difference checks also cover both
local and full-mixture analytic gradients, coordinate permutations, and the
deadline fallback.

To reproduce public-example and perturbed-instance checks from this directory:

```sh
python benchmark.py /path/to/participant/input --refit
```

The benchmark uses a 120-second subprocess timeout and an 8-GiB address-space
limit. Perturbations change temperature, increase inter-region interactions,
add coupling and field disorder, and apply fresh site permutations and spin
gauges. Exact results and fitted artifacts are saved under `validation/`.
Omit `--refit` to check the saved artifacts without rerunning their fits.

## Measured results

Final-source runs on the supplied public examples, with complete enumeration:

| Family | Champion reverse KL | Submitted reverse KL | Population ESS |
| --- | ---: | ---: | ---: |
| Quartets | 0.038197 | 0.002181 | 0.992232 |
| Quintets | 0.103123 | 0.002529 | 0.978344 |
| Mixed | 0.146121 | 0.000480 | 0.991337 |

The public mean reverse KL is **0.001730 nats**, or **1.81%** of the
champion's mean. Every public family satisfies the requested absolute and
champion-relative KL bounds. These final-source runs take 105.9–110.4 seconds;
the maximum measured child RSS is 907.3 MiB, under an enforced 8-GiB address
limit with four available CPU cores.

Six additional temperature/disorder/interaction/gauge perturbations all pass
artifact validation. Across all nine saved cases, the largest reverse KL is
**0.002529 nats** and the smallest population ESS is **0.950873**. These are
public and synthetic checks, not claims about access to unseen instances.

Detailed measurements are in `validation/results.json` and
`validation/summary.json`; final-source rerun logs are in
`validation/final_verification.log`. Runtime-source hashes are recorded in
`validation/source_sha256.txt`. The optional `development/` directory contains
exploratory outputs and is not used by the solver.
