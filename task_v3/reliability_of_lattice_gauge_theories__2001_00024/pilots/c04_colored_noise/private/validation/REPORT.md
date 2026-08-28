# Minimal-ready validation report

Status: **ready for the main tournament**, 2026-08-27 local. No fresh participant
agents were run. `attempt/` is strictly empty. Submit a directory containing root
`solver.py`; use `private/evaluator.py --submission DIR --participant DIR --split
screening --output JSON`. The participant override defaults to this pilot's
`participant/`. All solver execution uses the shared isolated runner; the evaluator
never imports a submission or falls back to trusted execution.

## Measured screening results

Both rows below are **actual isolated CLI runs**, nine cases each, 9/9 successful.

| Solver | mean_core | worst_family | combined score | mean seconds | max seconds | max RSS KiB |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Reference | 1.000000 | 1.000000 | 1.000000 | 1.078 | 1.522 | 234864 |
| Weak baseline | 0.574067 | 0.572201 | 0.573507 | 0.599 | 1.007 | 95072 |

Times are the common worker's reported execution seconds, not whole-suite wall
time. The evaluator wall limit remains 60 seconds per case and memory limit 6 GiB.
Raw records: `reference_screening.json`, `weak_screening.json`. Reference component
means are all 1. Weak means: calibration 0.501743, audit 0.500000, dynamics 0.523216,
decision 0.944444. Weak family means: white/coherent 0.572201, pink/correlated
0.575000, brown/degenerate 0.575000.

An earlier 10-second reference preflight timed out without diagnostics; a later
trivial isolated probe passed, followed by both complete 60-second-limit screening
runs. The earlier timeout is retained in `isolation_preflight.json`, not hidden or
misrepresented as a solver score. No infrastructure workaround is in the evaluator.

## Private pools and independent evidence

- 9 screening cases: three per scientific family, Hilbert dimension 64 throughout.
- 6 separate challenge cases: collective white noise, tight budget/coherent errors,
  a white floor on 1/f noise, signed collective channels, coherent lifting of
  degeneracy, and a lower infrared corner.
- 3 fresh confirmation cases: reserved, never used for participant tuning.
- Challenge/confirmation reference and weak outputs are precomputed, but have
  **not** been run as participant/isolated split evaluations in this minimal pilot.
  Trusted weak means/worst: challenge 0.569684/0.559052; confirmation
  0.579233/0.575000. Trusted reference consistency is 1 on each split.
- `analytical_checks.json`: 22/22 checks pass. Includes H0/Gauss commutation,
  intended number conservation, initial target-sector membership, trace,
  Hermiticity, positivity, even-spectrum unitality, arbitrary degenerate-subspace
  rotations, analytical single-spin rates, collective dark states, detection of
  incorrectly split transitions, independently written two-spin jump matrices,
  independent exponential propagation, the zero-frequency limit, and noiseless
  inference of all three spectral models.
- Largest tested 64-dimensional trace/Hermiticity/rotation residual is below
  2e-15; negative eigenvalues are below 2e-16 in magnitude. These are independent
  invariant/limit checks, not official paper-author numerical verification.

## Author-only repairs before freeze

The interrupted bulk patch landed only part of the implementation; missing files
were completed without changing the physical dimension or shrinking the pools.
The requested root solver API and `--participant` override were added, and
`attempt/` was emptied. A pre-freeze review found that the supplied audit bath
initially reused the calibration-generating bath: this would leak the inference
answer. It was replaced with separately drawn audit parameters, all labels were
regenerated, and the checks and both isolated screening runs were performed on the
repaired cases. No participant results informed any change. The private generator
records generating parameters only in evaluator-side metadata, never in `case`.

## Validity caveats

The reference is a **new reimplementation** of the follow-up's explicit secular
formalism, not official author code and not a reproduced paper figure. Public
protocol extensions include finite-band noisy inference, infrared regularization,
correlated channels, and known actuator crosstalk. This is a defined weak-coupling
Markov/secular model, not exact non-Markovian 1/f trajectories. Full secularization
near small but unequal splittings is a modeling convention, not an experimentally
validated approximation. Reference accuracy is supported by the analytical tests,
not a second large-system package or empirical device data.

Decision selection is the easiest component in this minimal pool: large uniform
protection wins many cases, while low-strength and graded settings win others.
The weak policy consequently scores highly on decision alone. Calibration,
frequency-resolved audit, and all-action dynamics are independently necessary for
a strong total score; do not advertise this as a hard optimization-only benchmark.
Scores are smoothly anchored so the weak implementation is near 0.5, not zero.
The freeze manifest is `private/freeze.json`; all participant-facing scientific
conventions are in `participant/input/protocol.md`.
