# Active radial spectroscopy submission

`policy.py` is the self-contained submission entrypoint. It needs only Python,
NumPy, SciPy, and the standard library. It does not read training data, depend on
the current working directory, write files, or require a public-input import at
inference time. It uses one BLAS thread.

## Method

- Spend 24 calls on isotropic three-direction matrix tomography at eight times.
- Fit two ordered, positive rank-one low residues using analytic derivatives and
  deterministic multistart bounded nonlinear least squares.
- Marginalize the unknown matrix tail through an analytic Gaussian moment model.
  Its trace and traceless covariance components incorporate the public atom-count,
  Dirichlet-weight, energy, orientation, continuum, and tail-mass distributions.
- Infer tail mass from the observations and update the shape covariance to its
  estimated scale, retaining uncertainty in total mass.
- Allocate the remaining 48 calls in two adaptive batches. Greedy experimental
  design minimizes the sum of normalized marginal standard deviations, including
  the second low state and tail features as nuisance parameters. Candidate probes
  include matched and nulling directions for both fitted residues.
- Report canonical projective angles and curvature-based marginal intervals with
  a 10% calibration allowance. Every instance uses exactly 72 calls.

## Local validation

The supplied development tests use only the public generator and simulator.
They are not the official isolated tournament suite.

The frozen final policy passes all numerical targets on 1,200 fresh public
instances: seeds 600000 through 600199 in each of the six families.

| Metric | Measured | Frozen requirement |
| --- | ---: | ---: |
| Robust loss | 0.0342235 | at most 0.165 |
| Worst-family point loss | 0.0382780 | at most 0.22 |
| Overall marginal coverage | 93.396% | at least 80% |
| Worst-family marginal coverage | 92.125% | at least 60% |

All 1,200 cases pass query/answer validation and use exactly 72 calls. The slowest
direct numerical run takes 3.025 seconds with three concurrent test workers.
All six separate-process protocol checks pass; their maximum elapsed time is
3.431 seconds, including interpreter startup and oracle interaction.

`validation_summary.json` contains the family-level results, and
`protocol_final.log` records the isolated checks. Raw public-simulation results
and earlier development experiments are retained under `research/`.

Set `RADIAL_INPUT` to the provided `participant/input` directory, then run:

```
python test_policy.py --count 200 --seed 600000 --workers 3 --output fresh.jsonl
python check_protocol.py
```

The first command validates query/answer schemas on every simulated case and
records parameter errors, coverage, timing, and family-balanced scores. The second
launches a fresh process per family, uses scratch as its working directory,
clears the child's environment, and enforces the 2 GiB address-space and 45-second
CPU limits while checking all JSONL messages and wall-clock deadlines.
