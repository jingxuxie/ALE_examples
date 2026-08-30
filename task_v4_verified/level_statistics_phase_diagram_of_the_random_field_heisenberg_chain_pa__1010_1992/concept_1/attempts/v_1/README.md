# Fast spin-fraction prediction

Run `python3 predict.py`. The program loads its assets, warms the numerical
solver, and flushes `READY`. Send the single JSON request described in the
task; the program returns one prediction per ID and exits. No public data
files, family labels, network access, or writable submission directory are
needed at inference.

## Method

- A 200-tree ExtraTrees regressor uses the supplied 250 symmetry-invariant,
  site-order-sensitive descriptors.
- A compact native evaluator stores tree thresholds in double precision
  and leaf values in single precision. It reproduces the original forest
  predictions to better than 1e-7, without loading scikit-learn at runtime.
- The regressor is trained on the 1,600 public training records plus 6,400
  new, balanced samples from the public generator, labeled using the
  supplied float64 physics implementation. Validation and the two fresh
  check sets are excluded from fitting.
- Four numerical threads also diagonalize the L=10 Hamiltonians in single
  precision. These calculations use the periodic, zero-magnetization
  sector and average the 84 middle-third eigenstate ratios, not a ratio of
  averages. Moments are accumulated in double precision. Spectra with
  closely spaced central eigenvalues are recomputed in double precision.
- Tree disagreement prioritizes the cases to diagonalize. After a
  one-second compute budget, remaining queued jobs are canceled, active
  jobs finish, and the surrogate supplies every uncomputed prediction.
  This leaves time for serialization, flushing, and shutdown. L=12 uses
  the trained surrogate.
- Field shifts, rotations, reflections, and global spin inversion preserve
  the physical target. IDs are used only to associate inputs and outputs.

## Runtime files

Only `predict.py`, `fast_physics.py`, `descriptors.py`, `native_forest.py`,
`forest.npz`, and `forest.so` are required. Dependencies are the supplied
system Python, NumPy, and SciPy. The shared library is built for the
provided Linux x86-64 environment and needs only the standard C/math
libraries. BLAS parallelism is limited to one thread per call.

## Measured results

The final implementation passes the accuracy and complete-response limits
on all 13 local streaming runs, using four-core affinity and a 2,048 MiB
address-space limit. Each held-out set contains 320 balanced cases.
The accuracy range reflects how many numerical refinements finish within
the adaptive compute budget under varying CPU contention.

| Held-out set | Runs | Overall RMSE range | Maximum family RMSE |
| --- | ---: | ---: | ---: |
| Public validation | 9 | 0.01595–0.02130 | 0.02315 |
| Fresh set 1 | 2 | 0.01905–0.02266 | 0.02603 |
| Fresh set 2 | 2 | 0.01873–0.02640 | 0.02851 |

Maximum complete-response time is 1.471 seconds; maximum startup time is
12.547 seconds. The mixed-precision L=10 solver has RMSE 0.00001304 and
maximum absolute error 0.0002535 against 1,280 float64 reference labels.
Native forest export changes predictions by at most 0.000000019 in its
equivalence check. The surrogate alone, before numerical refinement,
also passes all three held-out accuracy checks in `training_report.json`.

## Reproduction and checks

- `build_model.py` reproduces the additional simulations and model fit.
  Its generator seed is 29475631. The original baseline is retained only
  as the source of training hyperparameters.
- `python3 export_forest.py` exports `trained.pkl.gz` into the compact
  runtime assets, compiles `forest.c`, and verifies prediction equivalence.
  Rebuilding requires scikit-learn and a C compiler; inference does not.
- `generate_checks.py` produces two independent 320-case check sets using
  seeds 873292 and 873293 and the public float64 physics.
- `python3 test_physics.py` checks numerical accuracy against 1,280 labeled
  L=10 cases and tests the physical symmetries.
- `python3 test_submission.py --plain` checks the exact no-argument
  streaming interface on public validation, with four-core affinity and
  a 2,048 MiB address-space limit.
- `python3 test_submission.py --data independent_1.jsonl --report independent_1_report.json`
  checks a fresh dataset; substitute `independent_2` for the second set.

The JSON reports contain measured local accuracy and timing, including
startup, complete-response, and process-exit times. These are local checks,
not an official isolated evaluation or a claim about hidden labels.
The protocol's three-second clock ends at the complete flushed response;
process-exit time is recorded separately and is not used as that clock.
