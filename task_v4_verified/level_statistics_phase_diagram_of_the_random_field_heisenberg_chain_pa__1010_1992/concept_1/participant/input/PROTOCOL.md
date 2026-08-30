# Generation 2 protocol: L14-only grading

This is Concept 1, generation 2, champion-ratchet 1, not a separate
fourth concept. The observable and numerical accuracy targets are
unchanged; every graded realization now has fourteen sites. Paths in
this document are relative to the participant directory.

## Exact observable

Use the spin-1/2 Hamiltonian

`H = sum_j [h_j S_j^z + S_j . S_(j+1)]`, with periodic boundaries and `J=1`.

Work exclusively in total `Sz=0`. For `L=14`, the Hilbert-space dimension
is `binomial(14,7)=3432`. Sort eigenstates by ascending energy and select
zero-based ranks `1144 <= n < 2288`: exactly 1,144 eigenstates. Define

`M = sum_j exp(2*pi*i*j/14) S_j^z`

and predict

`f = mean_n [1 - abs(<n|M|n>)**2 / <n|M†M|n>]`.

This is the mean of eigenstate ratios, not a ratio of summed moments.
The observable is dimensionless in `[0,1]`. Field order matters. The
frozen executable definition is `workspace/physics.py`, identical to
the trusted evaluator copy. Labels use float64 central-subset
`scipy.linalg.eigh(..., driver="evr")` eigenvectors. The corresponding
L10 and L12 auxiliary labels use the same definition and each size's
own first Fourier mode and middle-third ranks.

Source: Pal and Huse, *The many-body localization phase transition*,
Phys. Rev. B 82, 174411 (2010), arXiv:1010.1992, Eq. (6).

## Complete sampling law

`workspace/generators.py` is the full public generator, supporting
`LENGTHS=(10,12,14)`. The distribution is not a secret. The common
amplitude is uniform on `[0.4,1.8]`, `[1.8,4.5]`, or `[4.5,8.0]`, with
probabilities `0.2`, `0.5`, and `0.3` respectively. Each vector is also
randomly translated, reflected, and globally sign-flipped. Continuous
site noise and rejection of field spacings `<=1e-8` ensure nondegenerate
bare fields. There are four families:

- `iid_uniform`: independent fields uniform between minus and plus the
  sampled amplitude.
- `ordered_blocks`: two or three contiguous, nearly equal-sized blocks
  with independently drawn centers, small internal slopes and noise;
  boundary detuning is weak-link-like, but exchange couplings remain 1.
- `alternating_correlated`: a staggered field plus a first-harmonic
  correlated component and continuous site noise.
- `shuffled_pairs`: pairs of nearby but distinct field values, placed
  at random sites on the ring.

Exact parameter intervals, randomization order and rejection logic are
in the executable generator. Fields alone determine the target; no
unobserved seed, amplitude, family label or other physical parameter is
needed at inference. Family and amplitude are not inference inputs.

## Data and permitted use

All label files are JSON-lines with `id`, `L`, `fields`, `family`, and `f`.
The 320 new L14 training records contain 80 per family. The 160 new L14
validation records contain 40 per family. The private 320-case L14 test
contains 80 per family and follows the same generator law. Its vectors
and labels are unavailable during search and are not mounted at startup.
New training and validation use independent OS-derived seeds published
in `input/data_checks.json`. All supplied splits are checked for
translation, reflection, global-spin-flip and uniform-field-shift
equivalence, as well as direct duplicates.

`input/auxiliary_train_L10_L12.jsonl` preserves the original 1,600 public
training records. `input/auxiliary_validation_L10_L12.jsonl` preserves
the original 320 public validation records. Both are auxiliary training
data in generation 2; **neither is a held-out generation-2 scoring set**.
They contain 200 and 40 records per family/length respectively. They
are included to make cross-size information available, not to promise
that a size-independent estimator is adequate.

You may train on all public labels, including the new public validation
labels if desired, and may simulate additional samples using the public
physics and generators. The supplied baseline uses new L14 training
plus both auxiliary splits, leaving new L14 validation out of its fit.
No previous fresh-agent model, solution code, private bank or private
ratchet evidence is supplied. Private evaluation artifacts must not be
accessed. The one-hour search allowance permits at most eight concurrent
simulation workers and one BLAS thread per worker.

## Official streaming interface

The evaluator runs `python3 /submission/predict.py` without arguments.
Load model assets during startup, then write exactly `READY\n` and
flush stdout. Startup has a separate 60-second allowance. No hidden
case file exists or is mounted during this phase. The parent then sends
one JSON line and closes stdin:

`{"cases":[{"id":"case_00000","L":14,"fields":[...]}]}`.

Each `fields` vector has exactly fourteen finite numbers. The ID is an
opaque join key, not a physical feature. Hidden order is independently
shuffled before neutral IDs are assigned, so IDs do not encode family
or original stress-bank ordering. Return exactly

`{"predictions":[{"id":"case_00000","f":0.5}]}`.

Produce exactly one finite numeric prediction in `[0,1]` for each ID.
Booleans, strings, duplicate IDs, missing IDs, unknown IDs and extra
keys are invalid. Ordering is arbitrary. No additional stdout text is
allowed; diagnostics may go to stderr. Flush the response and exit.

The 3-second inference clock covers input delivery, parsing, feature
construction, prediction, serialization, response delivery and process
exit. Startup is excluded. CPU affinity is restricted to four cores and
cannot be expanded; address space is limited to 2,048 MiB. Network is
unshared. `/submission` and `/participant` are read-only; `/tmp` and
`/output` are writable. There is no persistent cross-evaluation cache.
The parent never imports submission modules or model artifacts.

The supplied starter also supports local file-based testing:

`python3 baseline/predict.py --input input/validation_cases.json --output predictions.json`

This convenience mode is not the official grading interface. Refit the
public baseline with `python3 workspace/train_baseline.py`. Copy its
resulting predictor, descriptors and weights together when submitting.

## Scoring and readiness

Both overall RMSE `<=0.035` and worst-family RMSE `<=0.050` are required.
All 320 graded records have L14; family metrics each use 80 records.
Errors are absolute on the physical `[0,1]` scale, not relative errors
or percentages. Resource failure or invalid output fails independently
of numerical accuracy. No numerical threshold change is authorized by
this package; main records the final freeze before a fresh launch.

Results include `core_score` (overall RMSE), `worst_family_score`
(worst-family RMSE), `valid`, `evaluator_valid`, `resource_score`,
`runtime_seconds`, `passed`, and `reason`. Lower RMSE is better. A valid
but inaccurate submission remains a valid evaluation. Infrastructure
errors are distinguished from submission failures. Public data checks
and baseline validation metrics are in `input/`; official isolated
timing and hidden evaluation are performed by main.
