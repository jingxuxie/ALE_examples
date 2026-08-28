# Repair a regional decoder's logical-risk estimates

## Professional objective

You are taking over a prototype soft-output decoder for a quantum-error-
correction experiment. Its hard fault hypotheses sometimes reproduce the
detector record, but its reported logical risks are not trustworthy. The
experiment now needs **joint logical posterior probabilities**, not just a
low-weight fault vector. A calibration mode is shared by all shots in a batch,
and some detector observations are missing.

Repair or replace the scientific implementation in `software/`. Deliver an
executable decoder that remains accurate when hardware regions are coupled,
checks are redundant or erased, and calibration support changes. The prototype
is intentionally not a validated algorithm; retaining its architecture is not
required. Use the supplied diagnostic evidence to identify and test substantive
failures before choosing your final approach.

## Provided files

- `software/solve.py`: working JSON command-line plumbing.
- `software/binary.py`, `software/regional.py`, `software/inference.py`: an
  incomplete regional hard-decision implementation and its probability adapter.
- `software/validate.py`: behavioral comparison tool, not a hidden evaluator.
- `input/micro.json`, `input/micro_expected.json`: tiny networks with independent
  exhaustive-enumeration truth, including degeneracy and missing observations.
- `input/validation.json`, `input/validation_expected.json`: larger development
  networks and their reference probabilities. These are useful for both accuracy
  diagnosis and runtime experiments. They are not the held-out test set.

## Scientific model

Each input case is one batch. Draw a single latent mode `z` from `mode_prior`.
Conditional on that same mode, faults are independent Bernoulli variables within
each shot, and shots are independent. Fault `j` has mode-conditional probability
`faults[j].probabilities[z]`. Different entries describe independent **mechanisms**:
identical detector supports do not make two mechanisms mutually exclusive.

All detector and logical algebra is over GF(2). A mechanism toggles every detector
in its `detectors` list. For fault vector `e`, the complete detector record is
`H e mod 2`, where column `j` of `H` is that list. Only observed rows are
conditioned on: `null` in a shot's `syndrome` means the detector was not observed,
not that it measured zero. Dependencies among rows are allowed.

The shot's logical label is the bitwise XOR of `logical_mask` for every active
fault. Bit `b` of this nonnegative integer corresponds to logical observable `b`.
Faults with no detector support can still change the logical label. Faults with
zero logical mask still contribute probability mass. Multiple fault vectors
can have the same detector record and logical label, and their probabilities
must be **summed**, not maximized. `logical_mask` is supplied by the experiment;
you do not need to derive logical operators or a stabilizer code.

A shot query lists distinct fault indices. Its event is that the XOR of those
faults is one. All requested posteriors, including each shot's logical and query
posteriors, are conditioned on **all observed detector records in the case**.
Consequently, another shot can change a shot's answer through the shared mode.
`log_evidence` is the natural log of the probability of the complete observed
batch, marginalized over the mode and every unobserved fault/detector value.

`detector_regions` maps detector indices to hardware-region identifiers. It is
metadata, not a declaration of probabilistic independence. Some mechanisms touch
multiple regions. Region numbers, detector order, and mechanism order carry no
likelihood or elimination-order meaning.

## Interface

Submit a directory containing `solve.py` and all its local modules. The evaluator
runs this command from that directory:

```
python solve.py --input /absolute/path/cases.json --output /absolute/path/predictions.json
```

Input is `{"cases": [case, ...]}`. Each case supplies `id`, `num_detectors`,
`num_observables`, `detector_regions`, `faults`, `mode_prior`, and `shots`.
Each shot supplies `id`, `syndrome`, and `queries`, each with `id` and `faults`.
The provided JSON files are complete executable schema examples. Indices are
zero-based; IDs are opaque. All hidden batches have positive total evidence.
An individual mode may have zero likelihood for a batch.

Write `{"cases": [...]}`, preserving case and shot IDs. Each output case contains:

- `id`, `log_evidence` (a finite real number), and `mode_posterior` (normalized
  vector in the supplied mode order);
- `shots`, each containing `id`, `logical_posterior` (a normalized vector of
  length `2**num_observables`, indexed by the integer logical label),
  `logical_decision` (a maximum-posterior label; ties may be broken freely), and
  `query_probability` (mapping query IDs to their posterior probabilities).

Do not report independent per-observable marginals in place of the joint
distribution. No fault-vector recovery, canonical basis, or particular internal
representation is required. Extra diagnostic fields are allowed.

## Environment and resources

- Python 3.10 with NumPy 1.21 and SciPy 1.8 is available. Use the standard library
  and these packages; no network, installation, GPU, or external decoder is needed.
- Each evaluation invocation handles one batch and has **60 seconds**, one CPU
  thread, and **1.5 GiB address space**. Model authoring time is separate.
- Workloads have up to 320 mechanisms, 220 detectors, 3 modes, 4 shots and 4
  logical observables. There are 3--10 hardware regions. Each region touches at
  most 30 mechanisms wholly within it and at most 8 mechanisms crossing its
  boundary. A missing observation may change local rank.
- The networks are sparse and regionally structured, but not necessarily trees
  or graph-edge-only detector models. Full-batch fault enumeration is not a
  viable strategy. There is no requirement to use a specific local method.
- The supplied input and reference JSON must not be embedded in the submitted
  solver. Evaluation uses new probabilities, syndromes, row/column permutations,
  boundary topologies, and configurations with exact zero/one probabilities.

## Required deliverables and validation

Place everything in the requested output directory:

1. A self-contained executable submission rooted at `solve.py`.
2. `validation_predictions.json`, your final output on `input/validation.json`.
3. `diagnosis.md`, a concise explanation of the scientific defects you found,
   a measured before/after diagnostic, your main algorithmic choices, and the
   limitations you checked. Include actual commands and measurements; no long
   literature review is wanted.

For example, from a workspace containing your solver and `validate.py`:

```
python solve.py --input ../input/micro.json --output micro_predictions.json
python validate.py --expected ../input/micro_expected.json --actual micro_predictions.json
```

Adjust paths when working in the output directory. Run, inspect the discrepancy,
revise, and rerun on the larger public validation set before finalizing.

## Observable success

The principal score is scientific behavior on three held-out batches: joint
logical distribution (40%), parity-query probabilities (25%), batch log evidence
(20%), mode inference (10%), and logical decisions (5%). Full-accuracy bands are
total-variation error at most 0.02 for normalized distributions, absolute query
error at most 0.025, and absolute log-evidence error at most 0.08. These are
deliberately non-machine-precision tolerances. Larger errors receive graded
partial credit; a hard-output-only decoder is not a successful soft decoder.

Success also means completing the diagnostic loop, producing finite normalized
probabilities and executable artifacts, and staying within the resource envelope.
No source-code similarity, exact elimination order, or exact bytes are scored.
