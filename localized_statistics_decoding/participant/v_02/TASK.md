# Calibrate and deploy a burst-aware detector decoder

## Mission

An experiment's decoder was calibrated as if its fault rates were known and its
shots were identically distributed. Its logical-risk estimates fail after the
instrument starts drifting between noise regimes. You have **syndrome-only
calibration logs**, a small prototype, and public deployment diagnostics. Infer
a defensible noise model and deploy a soft-output decoder on new sparse detector
networks and dose schedules.

This is a system-identification and scientific-software repair task. The true
fault histories, calibration regime labels, and fault probabilities are not
provided. Choosing the model's complexity, fitting it from parity observations,
and integrating it with a scalable decoder are your responsibility. A single
hard fault hypothesis is not an adequate probability model.

## Files and workflow

- `input/calibration.json`: three small probe networks, rate-family membership,
  known mechanism biases, and a list of experimental settings.
- `input/calibration_records.npz`: arrays `setting` and `syndrome`, both shaped
  `(12000, 5)`. A row is one independent five-shot calibration sequence. Entries
  of `setting` index the metadata settings; each packed `syndrome` is the XOR
  detector record, with detector zero in the least significant bit. All probe
  detectors were observed. There are no fault or regime labels in this file.
- `input/micro.json`, `input/micro_expected.json`: small deployment checks.
- `input/validation.json`, `input/validation_expected.json`: larger public
  deployment checks. Their probabilities describe the experiment, not a
  prescribed fitted parameter vector.
- `software/`: executable but scientifically inadequate `train.py`, `solve.py`,
  binary algebra and diagnostic plumbing. You may repair or replace these.

Run the prototype, inspect its failures, and compare at least two materially
different calibration hypotheses or fitting choices using measured evidence.
Use that evidence to revise your model or implementation, then rerun deployment
validation. Splitting calibration sequences rather than individual shots avoids
leaking temporal information. You may refit your selected model on all records.

## Supported physical family

The experiment has an unknown number `K` of latent regimes, between one and
`max_modes=3`. Every sequence starts with a fresh draw from an unknown initial
distribution. Between adjacent shots, the regime follows an unknown,
time-homogeneous Markov transition matrix. The same parameters apply to
calibration and deployment. Regime labels are not physically identifiable;
do not infer meaning from an arbitrary label order. A single regime, an
independent-shot mixture, and persistent regimes are plausible hypotheses.

Conditional on the current regime, fault mechanisms in a shot are independent.
Mechanism `j`, belonging to `rate_group=g`, has probability `p_j` determined by

```
log(p_j / (1-p_j)) = offset[regime, g] + slope[g] * dose + bias[j].
```

`bias[j]` and `dose` are known. The offsets, slopes, initial distribution and
transition matrix must be inferred. Slopes are shared across regimes. The
physical parameters are constant across networks; the networks and grouping of
mechanisms vary. There is no extra temporal dependence once regimes are known.
Settings are independently randomized controls, not regime observations. A dose
does not itself modify the transition matrix. Rates are strictly between zero
and one. Single-mode and independent-shot models are subfamilies, not assertions
that they fit the data.

## Detector and logical semantics

All detector algebra is over GF(2). Each mechanism independently toggles every
detector in its `detectors` list. The complete detector record is `H e mod 2`,
where column `j` is that list and `e` is the binary fault vector. Duplicate
supports are separate independent mechanisms, not exclusive alternatives.
Dependent rows and columns are allowed.

In deployment, a shot's `syndrome` lists bits or `null`. Only actual bits are
conditioned on; `null` is an unobserved detector, not zero. Its logical label is
the bitwise XOR of `logical_mask` over active mechanisms. Label bit `b` is
observable `b`. A mechanism with no detector support can still affect the
logical label. Fault vectors compatible with the same record and label
contribute their **summed** probability, not just their maximum probability.

A query gives distinct fault indices and asks for the probability that their
XOR is one. Every requested shot posterior is conditioned on **all observed
shots of its deployment sequence**, including future records. You must report
the joint logical-label distribution, not a product of observable marginals.
`switch_probability[t]` is the posterior probability that the latent regime
changes between shots `t` and `t+1`, given the complete observed sequence.
`log_evidence` is the natural logarithm of its full observed-record probability,
integrating regimes and all unobserved fault and detector variables.

`detector_regions` is a detector-to-hardware-region map. It is not a declaration
of independence: faults can cross region boundaries. IDs, column order, row
order and region numbering are opaque. No particular factorization or decoding
algorithm is required.

## Interfaces and required output

Create a self-contained submission directory with these entry points:

```
python train.py --calibration /path/calibration.json --records /path/calibration_records.npz --output /path/model.json
python solve.py --input /path/cases.json --output /path/predictions.json
```

Train during development and save your fitted `model.json` beside `solve.py`.
The evaluator does not retrain it. The model file's internal schema is up to you;
the prototype schema is merely a starting point. Retain a reproducible training
entry point and any modules it needs. Do not embed reference prediction tables.

Deployment input is `{"cases": [...]}`. A case contains `id`, `num_detectors`,
`num_observables`, `detector_regions`, `faults`, and `shots`. A fault gives
`detectors`, `logical_mask`, `rate_group`, and `bias`. A shot gives `id`, `dose`,
`syndrome`, and `queries`. JSON examples are supplied in full.

Write `{"cases": [...]}` with matching case/shot IDs. Each case contains finite
`log_evidence`, `switch_probability` of length `number_of_shots - 1`, and `shots`.
Each output shot contains:

- `id`;
- `logical_posterior`: normalized probabilities indexed by integer label, length
  `2**num_observables`;
- `logical_decision`: any maximum-posterior label;
- `query_probability`: query-ID to posterior-probability mapping.

Also deliver `validation_predictions.json` and `diagnosis.md`. The latter should
record real baseline and final measurements, the alternatives you compared,
your selected calibration/inference approach, actual commands, and remaining
limitations. A short technical report is sufficient.

## Environment and resource envelope

- Python 3.10, NumPy 1.21 and SciPy 1.8; no network, installations, external
  decoder, or GPU is needed. You may use standard-library modules.
- Deployment: one sequence per invocation, one CPU thread, **60 seconds** and
  **1.5 GiB address space**. Training happens beforehand within your authoring
  time; a fitted artifact is required.
- Up to 320 mechanisms, 220 detectors, 8 shots and 4 logical observables.
  Networks have 3--10 regions. Each region has at most 30 wholly internal
  mechanisms and at most 8 crossing mechanisms. Full-network enumeration is
  not viable. Probe networks are much smaller than deployment networks.
- Held-out cases use new detector networks, longer sequences, masks, and dose
  schedules. Calibration uses doses -0.8, 0 and 0.8; deployment may reach ±1.4.
  The specified log-odds law remains valid there. This is transfer under a known
  physical family, not permission to assume constant rates outside calibration.

## Observable success

The score measures final predictive behavior on three withheld sequences, not
whether your coefficients match a secret parameter vector: joint logical
probabilities (40%), fault-parity query probabilities (20%), normalized
log-evidence accuracy (20%), and regime-switch posteriors (20%).

Full-accuracy bands are logical total-variation error ≤0.03, query absolute error
≤0.03, switch-probability absolute error ≤0.04, and log-evidence absolute error
divided by the number of observed detector bits ≤0.01. The evidence normalization
allows finite-calibration uncertainty; these are not floating-point tolerances.
Larger errors receive partial credit. Finite normalized probabilities, robust
execution, and truthful diagnostic artifacts are also required for a pass.

You can run `validate.py --expected ... --actual ... --input ...` from your
workspace to see the same kinds of discrepancies on public cases. Passing small
probes does not demonstrate scalable deployment or correct temporal inference.
