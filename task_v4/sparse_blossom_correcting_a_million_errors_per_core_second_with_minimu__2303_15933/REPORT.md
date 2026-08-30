# Hardness-discovery results

## Concepts and verification modes built

Three concepts, eight task generations, and fifteen scientific fresh-agent attempts
were completed. Every attempt used `ultima-alpha`, the supplied allowlist runner,
an initially empty writable output, and a one-hour ceiling. Participant and
evaluator hashes match their launch freezes; original submissions are preserved.
Two stdin-related preflights are excluded as infrastructure failures.

| Concept | Verification mode | Built generations | Ratchet generations | Final status |
|---|---|---:|---:|---|
| Correlated logical-class decoding under a compute cap | A — baseline improvement | 2 | 1 | `hard_open_candidate` |
| Calibration-robust physical-MAP/logical-posterior inversion | B — counterexample construction | 3 | 2 | `hard_open_candidate` |
| Budgeted active calibration of correlated detector channels | E — active experiment design | 3 | 2 | `solved` |

## Baseline, champion, and fresh-agent scores

### Concept 1: baseline improvement

| Generation | Supplied baseline/champion | Fresh attempt 1 | Fresh attempt 2 |
|---|---|---|---|
| 1 | 1,523 errors / 12,288 shots | 153 errors; 89.954% reduction; passed | Not launched |
| 2 | 427 errors / 3,072 shots; 107.964 CPU seconds | 389 errors; 8.899% reduction; 126.107 CPU seconds; failed | No official quality score: worker killed; failed |

Generation 2 fixes targets of at least **20% pooled reduction**, **15% holdout
reduction**, no family error-count regression, positive paired confidence, and
**132 CPU seconds**. Attempt 1 reaches 11.163% holdout reduction and 0% worst-family
reduction. Its paired 95% interval for pooled relative improvement is
**[4.020%, 13.779%]**, entirely below the target.

Attempt 2's initial kill alone did not identify its cause. One unchanged official
replay was killed at the configured hard CPU boundary. A separately labeled,
nonqualifying 180-second diagnostic completed at **156.480 CPU seconds**, with
384 errors, **10.070% pooled** and **12.093% holdout** reduction, and a nonuniform
crosstalk regression from 113 to 117 errors. It fails the original resource and
all three principal quality gates; it is not substituted for the official score.

### Concept 2: counterexample construction

The normalized minimum certificate score must reach **1.0**. Valid JSON/input
constraints alone do not constitute a valid witness.

| Generation | Supplied baseline/champion score | Fresh attempt 1 | Fresh attempt 2 |
|---|---:|---:|---:|
| 1 | 0, deliberately weak | 1.008928623; passed | 1.008929900; passed |
| 2 | 0.939363803 | 1.010410901; passed | 1.010407940; passed |
| 3 | 0.919789901 | 0.977183708; failed | 0.977184879; failed |

Each final fresh witness has one actual posterior-failing path and seven
additional certificate-only failures. Actual minimum opposite-class posteriors
are **0.844370599** and **0.844370848**, below **0.845**; worst anchor scores are
0.997171100 and 0.997172220. The miss is small but real, not solely a loose bound.
This establishes failure of the declared robust witness construction, not an
inability to find any qualitative MAP/posterior inversion.

### Concept 3: active experiment design

Entries are **mean / worst regime-family log RMSE**; lower is better.

| Generation | Runnable weak baseline | Fresh attempt 1 | Fresh attempt 2 | Fixed target |
|---|---|---|---|---|
| 1 | 0.084158 / 0.164497 | 0.055933 / 0.133077; failed | 0.050292 / 0.089073; passed | 0.055 / 0.095 |
| 2 | 0.105738 / 0.166973 | 0.050151 / 0.062246; passed | 0.050706 / 0.069639; passed | 0.075 / 0.125 |
| 3 | 0.133674 / 0.210986 | 0.056575 / 0.075526; passed | 0.056298 / 0.073771; passed | 0.090 / 0.140 |

Actual best fresh submissions, not private references, were promoted after each
solved generation. The final champion is generation-3 attempt 2. Both final
attempts stay below 16 CPU seconds per episode against a 60-second cap, with all
query, shot, and memory constraints satisfied. A private latent-blind reference
also passes the final task at **0.070182 / 0.113583**, maximum 25.575 CPU seconds.

## Counterexample and adversarial search results

- **Decoding:** private stress found overlap, nonuniform crosstalk, and space-time
  memory families where the first champion loses accuracy. The new suite uses
  unconditional samples, not label-selected failures. On independent private
  confirmation, fourfold ensembles reduce 101 errors to 95 (5.94%) at 4.65 times
  the CPU; the smaller pilot improves from 58 to 45 at 4.93 times the CPU. An
  optimistic budget-matched choice removes 3.96% on confirmation. Compiler,
  temperature, and matching-fallback controls do not qualify. These finite
  controls do not prove an optimum. No passing final-generation implementation
  is known.
- **Robust inversion:** the first search evaluated 12,590,228 proposals over
  5,105 restarts and found an achievable initial witness. The second generation
  was also privately achievable and solved by both fresh agents. The final
  extension adds explicit balanced orientation-conditioned paths at the same
  perturbation magnitude: the preceding champion fails nine paths pointwise,
  plus five certificate-only paths. A bounded final search over 18 restarts
  finds no passing witness; its best stricter-surrogate score is 0.965262610.
  The checker audits 5,791 inference anchors, off-anchor cases, symmetry, malformed
  inputs, and independent exact calculations. This is a union of 131 continuous
  one-dimensional paths, not a full calibration box, and not a defect in Sparse
  Blossom's minimum-weight-matching correctness.
- **Active calibration:** the initial first-attempt failure was noise-sensitive:
  three supplementary noise tapes all passed, and its four-tape diagnostic was
  0.051174 / 0.087479. It is not used as hardness evidence. Later private scaling
  tests exposed dense-state memory/CPU failures of the actual earlier champions
  on connected, active geometries. The selected generation-2 champion fails
  even at 24/28 detectors, below the integer-width boundary. Fresh agents repair
  the scaling weakness and pass both later generations. No final failed
  capability is established for this concept.

## Final status, solvability, and failed capabilities

**Selected task: concept 1, generation 2 — `hard_open_candidate`.** Its participant
packet is `concept_1/generations/generation_2/participant/`; its evaluator is
`concept_1/generations/generation_2/evaluator/evaluate.py`. The original concept-root
participant packet is the solved first generation and is preserved, not selected.

The failed capability is improving **joint logical-class decoding across
correlated-noise families within a strict compute budget and without family
regressions**. Solvability of the full target is **unknown**, not demonstrated.

Concept 2 generation 3 is an additional retained **`hard_open_candidate`**.
The failed capability is **certifiably robust counterexample construction across
all declared directional calibration paths**. Solvability is **unknown**; neither
a passing final witness nor an impossibility proof is known.

Concept 3 is **`solved`**, with solvability demonstrated by fresh and private
latent-blind policies. It is archived rather than retained as hard. The session
does not claim a `hard_verified_achievable` result.

The exact scores and isolation evidence are preserved in
`discovery/tournament_results.json` and `discovery/package_audit_final.json`.
