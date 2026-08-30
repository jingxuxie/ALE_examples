# Adaptive cross-resonance calibration controller

`solution.py` is the executable submission. Run it with `python3 -u solution.py`.
It accepts the task's line-JSON protocol on standard input, emits only protocol
messages on standard output, and requires only NumPy and SciPy. It does not read
any development data or depend on participant-directory imports.

## Method

- Evaluate the exact block-diagonal Hamiltonian exponential, including the
  relative control phase, with analytic derivatives for all nine parameters.
- Bootstrap with four signed zero-time calibrations and 64 short-time
  experiments, using 5,120 shots. Use bounded multistart fitting to resolve
  frequency and sign ambiguities. Compare both public nuisance regimes by fit
  quality rather than relying solely on a zero-time classification.
- Allocate the remaining shots in three adaptive batches of 4,096, 6,144, and
  9,216 shots, with respective maximum durations of 3.3, 8, and 12. Candidate
  experiments include conditional target measurements and control-coherence
  and parity measurements.
- Choose shots by nuisance-aware A-optimal Fisher-information reduction,
  weighted by the five published coefficient-normalization scales. Refit
  after each batch. The final fit uses moment-matched nuisance regularization
  based on the public distribution widths.
- Use at most 168 queries and 24,576 shots. Deadline guards retain the latest
  completed estimate if there is insufficient time for another fitting stage.

## Public development validation

The final file was tested with `input/local_simulator.py`, seed `715151`, and
32 episodes (eight per family), under the harness's resource and protocol
checks:

| Metric | Result |
| --- | ---: |
| Valid episodes | 32 / 32 |
| Mean NRMSE | 0.03779816 |
| Worst-family mean NRMSE | 0.05576578 |
| Aliasing mean NRMSE | 0.04795276 |
| Near-degenerate mean NRMSE | 0.02222461 |
| Weak-entangling mean NRMSE | 0.02524949 |
| Nuisance/decoherence mean NRMSE | 0.05576578 |
| Maximum solver wall time | 3.689 seconds |
| Maximum solver CPU time | 1.659 seconds |
| Shots per episode | 24,576 |

An additional 128 in-process recovery tests, using independently generated
public-family episodes with seed `417139`, gave mean NRMSE `0.03461856` and
worst-family mean NRMSE `0.04851547`. These additional tests checked experiment
validity and budgets, but were not independent process-resource tests.

The analytic probabilities agreed with the public forward model to below
`2e-16` on randomized settings. Finite-difference checks of all nine derivatives
agreed to below `2e-9`, including a separate zero-frequency check. Five further
corner cases covered high frequencies, vanishing conditional frequency, equal
conditional frequencies, and weak entangling coefficients.

These are public development results, not hidden-evaluation results.
