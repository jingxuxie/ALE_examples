# Burst-aware decoder: diagnosis and validation

## Baseline and scientific repair

I copied the supplied software into this submission directory, ran its training
entry point, and measured its predictions against both public diagnostics before
replacing the implementation. The retained `baseline_*` files reproduce that
measurement; the baseline solver now reads `baseline_model.json` so that rerunning
it cannot accidentally use the fitted final model.

The prototype substitutes detector occupancy for fault rates, sets every dose
slope to zero, and collapses all regime uncertainty. It turns missing detectors
into zeros and reports a delta distribution at an arbitrary binary-elimination
solution. Its evidence is the probability of that one fault vector rather than
the sum over compatible vectors. It neither smooths across shots nor estimates
regime changes. These are scientific errors, not merely numerical problems.

## Calibration hypotheses and selection

Only `calibration.json` and `calibration_records.npz` enter training. Public
expected predictions never enter the likelihood, optimizer, or model artifact.
I split the 12,000 entire five-shot sequences into 9,600 training and 2,400
holdout sequences using NumPy seed 7143. No shots from a sequence cross the split.

For every setting and candidate regime, I sum the independent Bernoulli weights
of all 4,096 fault patterns in the corresponding 12-mechanism probe, grouping by
the packed parity syndrome. This produces exact emission probabilities and
analytic derivatives. Forward-backward inference gives the sequence likelihood
and its gradients. L-BFGS-B fits regime offsets, shared dose slopes, initial
probabilities, and (for Markov models) transitions. Multimode hypotheses use three
deterministic starts. Optimizer bounds are numerical safeguards; the selected
physical coefficients are interior. Regime order is arbitrary and is only
canonicalized for a readable artifact.

Measured negative log likelihood, in nats per five-shot sequence (lower is better):

| Hypothesis | Training | Holdout |
|---|---:|---:|
| One regime, dose-dependent rates | 16.404205 | 16.275196 |
| Two independent-shot regimes | 16.317424 | 16.180559 |
| Three independent-shot regimes | 16.298113 | 16.149544 |
| Two Markov regimes | 16.157410 | 16.020512 |
| Three Markov regimes | **16.096587** | **15.948269** |

The three-mode Markov model gains 0.201274 nats/sequence over the three-mode
independent mixture, with paired holdout standard error 0.013995. Its gain over
the two-mode Markov model is 0.072242, standard error 0.008158. Thus persistence
and the third regime have separate measured support; I did not select complexity
from public prediction errors. The selected model is refitted on all sequences,
achieving NLL 16.066633 per sequence. Its shared slopes are approximately
`[0.896660, -0.606785, 0.390780]`; the full fit is in `model.json`.

After selection, I also refitted the single-regime, three-mode independent, and
two-mode Markov alternatives on all records and ran the same exact deployment
decoder. Their worst public-validation logical TV errors were respectively
0.415831, 0.172438, and 0.170967, versus 0.016360 for the selected model.
The independent three-mode model's worst switch error was 0.378892, versus
0.034801 for the selected model. See `audit_results.json` for all measurements.

## Deployment inference

`solve.py` loads its neighboring fitted artifact and delegates to `inference.py`.
Only observed detector rows are conditioned on. Within a region, GF(2) row
reduction produces affine internal-fault solutions for each assignment of its
crossing mechanisms. I sum all compatible independent-fault probabilities,
including duplicate columns and detector dependencies. When the local nullspace
would be large, an alternative XOR-state dynamic program uses the internal
detector rank instead. No full-network fault enumeration is performed.

Regional factors retain shared crossing variables, which are eliminated jointly;
the hardware regions are not assumed independent. The shared fault prior and
logical/query sign of a crossing mechanism appear exactly once. Detector-silent
mechanisms have separate exact factors. Walsh characters carry every joint
logical-label probability and each requested fault-parity expectation through
the contraction. The inverse transform recovers the joint label distribution,
not a product of marginal observables. Feature batching limits tensor memory.

Per-regime shot evidence feeds scaled forward-backward smoothing over the entire
sequence. Smoothed regime probabilities mix conditional shot outputs, and
two-slice posteriors give switch probabilities. Local scaling and log-domain
sequence evidence avoid multiplying many tiny shot probabilities directly.

## Public measurements

These are maximum errors across shots/queries/transitions within each case;
evidence error is divided by the total number of observed detector bits.

| Case / implementation | Logical TV | Query absolute | Switch absolute | Evidence/bit |
|---|---:|---:|---:|---:|
| dose_ring / prototype | 0.993264 | 1.000000 | 0.922405 | 0.542149 |
| dose_ring / final | **0.005149** | **0.003620** | **0.020198** | **0.000205** |
| drift_ladder / prototype | 0.961242 | 1.000000 | 0.992335 | 0.383799 |
| drift_ladder / final | **0.016360** | **0.009736** | **0.034801** | **0.000151** |

Across all three micro cases, final maxima are logical TV 0.006355, query error
0.006250, switch error 0.007612, and evidence/bit error 0.002798. Every public
case is inside all four stated full-accuracy bands. Exact numerical results are
saved in `micro_metrics.json`, `validation_metrics.json`, and the baseline metric
files. Required final predictions are in `validation_predictions.json`.

## Independent checks and resources

- Exhaustive enumeration of every fault pattern and every regime path on the
  micro sequences agrees with the regional decoder to about 1e-15. This checks
  masked detectors, duplicate supports, silent mechanisms, joint logical labels,
  parity queries, future conditioning, switches, and evidence together.
- Forty randomized local algebra problems compare affine enumeration and the
  independent XOR dynamic program; maximum absolute discrepancy is 1.11e-15.
- Central finite differences check every three-mode HMM likelihood-gradient
  coordinate; maximum discrepancy is 2.23e-10.
- The public validation invocation took 0.23 seconds and about 45 MiB peak RSS
  in the initial final-decoder run; public micro took 0.18 seconds.
- A seeded synthetic stress case has 311 mechanisms, 220 detectors, ten regions,
  eight shots, four observables, 40 crossing mechanisms, and eight crossings per
  region. Doses include both -1.4 and +1.4; later shots have missing detectors.
  Its boundary elimination width is 18. It ran in 2.60 seconds at about 98 MiB
  peak RSS. A second run under a 1.5 GiB address-space cap and 60-second timeout
  completed in 4.96 seconds at about 98 MiB. All emitted probabilities were
  finite, normalized, in range, and had valid MAP decisions.

The synthetic case is a resource/consistency check generated from the fitted
model, not independent evidence of predictive accuracy. `audit.py` reproduces
the numerical checks, alternative-model comparisons, and synthetic input.

## Reproduction commands

All paths below refer to the actual mounted workspace available in this run.
The requested `/home/xuandong/...` spelling was not present; the available
submission root is `/srv/home/xuandong/.../attempts/v_02/fresh_01`.

```bash
BASE=/srv/home/xuandong/mnt/jingxu/ALE/tasks_v2/localized_statistics_decoding
INPUT=$BASE/participant/v_02/input
cd "$BASE/attempts/v_02/fresh_01"
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1

python baseline_train.py --calibration "$INPUT/calibration.json" --records "$INPUT/calibration_records.npz" --output baseline_model.json
python baseline_solve.py --input "$INPUT/validation.json" --output baseline_validation_predictions.json
python validate.py --expected "$INPUT/validation_expected.json" --actual baseline_validation_predictions.json --input "$INPUT/validation.json"

python train.py --calibration "$INPUT/calibration.json" --records "$INPUT/calibration_records.npz" --output model.json > training.log
python solve.py --input "$INPUT/micro.json" --output micro_predictions.json
python validate.py --expected "$INPUT/micro_expected.json" --actual micro_predictions.json --input "$INPUT/micro.json"
python solve.py --input "$INPUT/validation.json" --output validation_predictions.json
python validate.py --expected "$INPUT/validation_expected.json" --actual validation_predictions.json --input "$INPUT/validation.json"
python audit.py --input-dir "$INPUT" > audit.log
(ulimit -v 1572864; /usr/bin/time -f 'wall_seconds=%e max_rss_kib=%M' timeout 60s python solve.py --input synthetic_stress.json --output synthetic_limited_predictions.json)
```

## Remaining limitations

Predictions use fitted parameters rather than integrating parameter uncertainty;
finite-calibration uncertainty remains, especially when extrapolating dose.
The scientific model is restricted to the specified stationary Markov/logit
family. Exact boundary contraction is exponential in elimination width, not in
total mechanisms; arbitrary high-treewidth region graphs can exceed the resource
envelope even though the public cases and the larger width-18 stress case do not.
The implementation rejects algebraically impossible syndromes instead of
silently treating them as possible observations. No hidden cases or external
data were inspected, and no reference prediction table is used by the solver.
