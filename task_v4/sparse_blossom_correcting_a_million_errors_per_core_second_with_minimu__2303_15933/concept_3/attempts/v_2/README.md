# Active detector-channel calibration submission

Run the standalone submission with:

```sh
/usr/bin/python3 solution.py
```

It reads the specified JSON-lines protocol from stdin, flushes every query,
and emits one final positive rate per channel. It requires only NumPy and SciPy,
sets numerical libraries to one thread, and does not read any training data or
other submission files at runtime.

## Method

- Compute the exact full-syndrome likelihood, including the shared shot-mode
  mixture, alternate footprints, overlapping channels, and saturation.
- Factor the Walsh spectrum into three fixed parity matrices; use batched
  matrix multiplication and the fast Walsh transform for likelihood evaluation.
- Begin with a small pilot covering sector interventions and two intermediate
  gain levels for each rare channel. Identify these actions from exposures,
  rather than their descriptive names.
- Refit bounded maximum likelihood at 6,000, 14,000, 26,000, and 40,000 shots.
  Between stages, use importance-weighted Sobol quadrature to estimate posterior
  log-rate means and covariance under a bounded log-uniform reference prior.
- Optimize subsequent allocations using full Fisher matrices, current posterior
  precision, and a family-balanced variance criterion. Reserve sufficient query
  slots to finish within the protocol limits.
- Return the exponential of the posterior mean log rate. Final integration uses
  4,096 points, with a larger integration only if importance weights degenerate.

## Validation

The submitted file was run on all six supplied episodes using the supplied
`input/local.py`, and separately with a strict protocol checker and an independent
event-level sampler implementing mode selection, channel firings, alternate
footprints, and XOR syndromes. The strict checker applies the 60-second CPU and
3-GiB address-space limits to each fresh worker.

| Test | Mean family log RMSE | Worst regime/family log RMSE |
| --- | ---: | ---: |
| Six supplied episodes, disclosed multinomial seeds | 0.047160 | 0.109109 |
| Six supplied episodes, independent event sampler | 0.048368 | 0.086539 |
| Development: 150 fresh log-uniform-rate simulations | 0.049636 | 0.059339 |
| Development: 60 resampled supplied episodes | 0.049891 | 0.065386 |

The disclosed six-episode draw exceeds the 0.095 worst-cell target, driven by a
large hook-rate error in one episode. Its mean meets the 0.055 target. The
independent event-sampling draw meets both numeric targets. These are development
checks, not an official twelve-episode hidden-suite pass.

The final strict tests use exactly 40,000 shots per episode, respect all query
limits, and peak below 18 CPU seconds and 150 MiB resident memory. Development
Monte Carlo runs use the same selected allocation strategy with 2,048 rather
than 4,096 final quadrature points.

## Reproduction

From this directory:

```sh
/usr/bin/python3 ../../participant/input/local.py --episode 0 --workdir "$PWD" -- /usr/bin/python3 "$PWD/solution.py"
/usr/bin/python3 validate_protocol.py --sampler multinomial --seed-offset 0 --output final_training.json
/usr/bin/python3 validate_protocol.py --sampler events --output final_events.json
/usr/bin/python3 test_solution.py
```

`experimental.py`, `experiment.py`, and the saved experiment reports retain the
development comparisons. They are not dependencies of `solution.py`.
