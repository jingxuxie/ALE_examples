# Independent author-side contract and shortcut audit

Audit date: August 27, 2026 PDT / August 28, 2026 UTC. Paths below are relative
to `tasks_v3/implementation_strategies_in_phonopy_and_phono3py__2301_05784`.

## Decision summary

**Do not infer substantive fitting success from a score above 0.70, or accept
its difficulty merely because a fresh model scores below 0.70.** A generic
all-zero output scores **0.754597950053** over the current six cases and
**0.728835414233** on their heldout subset. It learns neither tensor and predicts
zero forces. The suspected calibration shortcut is confirmed.

**Grid has a related, localized calibration problem, not a missing flat-CDF
convention.** Zero spectra and one zero image shift per query score
**0.999944342553** on `heldout_flat_79043`, despite a completely missing CDF and
incorrect image sets. That shortcut scores only **0.446337158085** across all
ten cases: this does not establish a universal grid solver.

Polar secondary degeneracy and cubic phase are explicitly specified. No genuine
missing convention was found in those targeted checks. Polar's unqualified
claim that its measured starter scores 0.5 is inaccurate under its documented
scientific floors; the current starter mean is **0.623899903199**.

### Pilot context supplied by the main author

After the direct scoring audit, the main author reported initial fitting quality
approximately **0.911**, with both Si8 branches approximately **0.478**, exact
results on the realistic 64/128/512-atom cases, and grid/cubic/polar approximately
**1.0**. These are **user-reported results, not independently inspected pilot
artifacts**. They are not evidence of task hardness. The main author owns the
separate Si8 ill-conditioning / public-minimum-norm versus hidden-estimator
investigation; this audit does not duplicate it or certify that estimator
convention. Its bounded public-contract check must not be read as settling that
open issue.

The confirmed zero shortcut does **not** depend on Si8: the three heldout cases
alone score **0.728835414233** for zeros and **0.915821095243** for privileged
reference-fc2/zero-fc3. Retain those scoring findings independently of any Si
reference correction. Given the reported successful pilots, no hardness-based
acceptance claim follows from this audit or from the isolated Si failure.

**No live evaluation scales, contracts, reference files, or participant files
were changed. No attempt contents or model logs were inspected.** All new files
are confined to this report and `author/contract_audit/`. Public participant
TASK/CONTRACT files were read only. Author baseline/reference evidence was read;
no pilot output was evaluated. These are trusted direct `score_case` audits,
**not sandbox/runtime tests**. No model invocation, bwrap run, or source rebuild
was used. Nineteen watched contract/scoring/manifest files have unchanged hashes.

## 1. Fitting: confirmed score shortcut

### Measurements under the unchanged current scorer

`author/contract_audit/fitting_ablations.json` contains all 24 direct-score
records, full branch metrics, input/reference/baseline hashes, and artifact
paths. Twelve actual NPZ ablation outputs are saved under
`author/contract_audit/outputs/`.

| Output | All-case mean | Heldout mean | Worst family | Worst family component |
| --- | ---: | ---: | ---: | ---: |
| Stored measured weak | 0.500000000000 | 0.500000000000 | 0.500000000000 | 0.500000000000 |
| Generic zero fc2 and fc3 | 0.754597950053 | 0.728835414233 | 0.722566108026 | 0.721340400041 |
| **Privileged reference-fc2 / zero-fc3 ablation** | 0.920108647484 | 0.915821095243 | 0.914738632143 | 0.834999669285 |
| Stored constrained reference | 0.988677345921 | 0.998180341836 | 0.943527649277 | 0.887228960456 |

The harmonic-only row uses **hidden reference fc2**. It is a privileged
diagnostic of omitting cubic fitting while retaining the reference harmonic
tensor, **NOT a generic solver, an independently fitted harmonic baseline, or
evidence that a participant can obtain that fc2**. The zero-tensor output uses
only input-defined shapes and does not access expected values to construct it.

| Case | Zero tensors | Privileged harmonic-only | Stored reference |
| --- | ---: | ---: | ---: |
| `initial_nacl_64_512` | 0.739552896689 | 0.914484751813 | 0.994171006722 |
| `initial_si_8` | 0.882243618604 | 0.943422778095 | 0.943527649277 |
| `initial_gan_32` | 0.719284942325 | 0.915281069268 | 0.999824394021 |
| `heldout_mgo_64_512` | 0.732398490725 | 0.914992512473 | 0.995004517547 |
| `heldout_sno2_72` | 0.728260478249 | 0.917131149060 | 0.999717511204 |
| `heldout_gan_128` | 0.725847273727 | 0.915339624196 | 0.999818996756 |

Each stored weak case scores exactly 0.5. Current rescoring reproduces all six
weak and all six reference scores in
`concepts/fitting/private/reference/author_measurements/validation.json`;
the stored-reference mean also matches `author/fitting_scorer_crosscheck.json`.
The comparison is recorded in `author/contract_audit/validation.json`. Stored
reference rescoring is not a new independent reference run or runtime result.

### Root cause and raw errors

At `concepts/fitting/private/evaluator.py:55`, each branch adds tensor-relative
error, acoustic/permutation/space-group residuals, and heldout-force RMSE divided
by observed force RMS; the cubic branch also adds support residual. At
`concepts/fitting/private/evaluator.py:34`, quality is
`1 / (1 + branch_error / max(weak_branch_error, 1e-10))`.
`concepts/fitting/private/reference/physics.py:53` computes homogeneous
invariance residuals, all exactly zero for zero tensors. This is mathematically
correct invariance checking, but a poor combined calibration.

For **every** zero-output case:

- fc2 and fc3 tensor-relative errors are both **1.0**.
- Acoustic, permutation, space-group, and support residuals are **0.0**.
- Heldout-force RMSE equals observed force RMS, so normalized force error is
  **1.0** on each scored force packet.
- Both branch errors therefore equal **2.0**, not a small physical error.

Most weak branch errors range from **5.070128160538** to **6.507273784025**;
normalizing by those large unconstrained errors gives zeros about 0.72–0.76.
For `initial_si_8`, the cubic weak branch error is **4761.907730110098**:
zero fc3 obtains **0.999580176588** even when fc2 is also zero. The stored Si
fc3 norm is approximately 0.0308822580 versus weak fc3 norm 146.9896458847.
That extreme tensor-error calibration further hides missing cubic physics.

The privileged harmonic-only outputs still have **fc3 relative error 1.0**.
Except for Si, their cubic branch scores are about **0.835–0.838**. For example,
`heldout_gan_128` has harmonic-only force RMSE **0.00284919141047**, versus
reference **0.000118317451110**, but the harmonic-only total score is
**0.915339624196**. Total-force normalization is dominated by the harmonic
signal and is not a test of recovering the cubic residual on its own.

There is a separate interpretation caution in `initial_si_8`: the reference
itself has heldout mixed-force RMSE **0.558678948217** against observed RMS
**0.675462670905**, normalized error **0.827105585967**, yet total quality is
**0.943527649277**. Reference tensor agreement is not absolute force accuracy.
This measurement alone does not establish an incorrect constrained reference;
heldout native-force residuals remain part of the existing definition.

### Fairness and acceptance implications

The public fitting objective and conventions are unusually explicit:
`concepts/fitting/participant/workspace/CONTRACT.md:26` defines force signs and
the half factor; `concepts/fitting/participant/workspace/CONTRACT.md:70` defines
compact expansion; `concepts/fitting/participant/workspace/CONTRACT.md:96`
defines folding; `concepts/fitting/participant/workspace/CONTRACT.md:113`
distinguishes joint and two-stage constrained fitting;
`concepts/fitting/participant/workspace/CONTRACT.md:140` defines invariances and
support. No targeted missing convention was found there.

However, the exact combined calibration is not stated in its public evaluation
section at `concepts/fitting/participant/workspace/CONTRACT.md:181`.
“Both tensors are compared” is true but does not convey how
100% tensor error can receive high credit. A real raw failure to recover either
tensor would be scientifically meaningful; the current scalar alone does not
demonstrate it. The acceptance language in `author/CANDIDATES.md:156` requires
reference >0.90, fresh score <0.70, and a substantive residual gap. Those first
two numerical checks cannot substitute for the third, given the zero shortcut.

## 2. Grid: flat contract is clear, flat scoring is weak

`concepts/grid/participant/workspace/CONTRACT.md:77` defines the simplex CDF;
`concepts/grid/participant/workspace/CONTRACT.md:89` explicitly describes the
flat point-mass jump, zero ordinary DOS away
from it, and exclusion of exact energy knots. Both flat reference cases have
five exactly flat branches. Their stored CDF equals the stipulated step with
**maximum absolute error 0**, and DOS is exactly zero. The minimum separation
of any sampling threshold from any input frequency over the ten cases is about
**1.46547133539e-7 THz**, safely above the stated 1e-10. There is no unresolved
point-mass endpoint ambiguity in these inputs.

But `concepts/grid/private/evaluator.py:53` normalizes distance by reference
distance RMS with a 1e-12 floor; `concepts/grid/private/evaluator.py:66` uses
reference-dependent DOS/CDF scales; `concepts/grid/private/evaluator.py:72`
then divides each combined error by the weak combined error. On flat
spectra the baseline's nonzero DOS can dominate that denominator and conceal a
wholly missing cumulative jump. The audit's generic output has one zero shift
per query, zero distances, and zero DOS/CDF, all with valid shapes/dtypes.

| Case / branch | Generic raw error | Weak raw error | Generic branch quality |
| --- | ---: | ---: | ---: |
| `pool_flat_17029` geometry | 0.484375 | 0.484375 | 0.500000000000 |
| `pool_flat_17029` spectral | 0.5 | 3423.277606181553 | 0.999853962477 |
| `heldout_flat_79043` geometry | 0.484375 | 11390368019.558250 | 0.999999999957 |
| `heldout_flat_79043` spectral | 0.5 | 4491.263646191383 | 0.999888685149 |

The resulting flat-case core scores are **0.749926981239** and
**0.999944342553**. Missing CDFs and image sets are genuine scientific errors,
not fairness disputes, but these scores nearly erase them. Across all ten cases
the generic shortcut scores **0.446337158085** case-weighted or
**0.403438550124** family-balanced; worst-family quality is **0.304128678171**.
Thus a fresh grid failure on nonflat/skew/boundary work can still be meaningful;
high flat-family quality alone does not validate the flat CDF or image logic.

## 3. Polar and cubic: conventions and quality claims

### Polar

At `concepts/polar/participant/workspace/CONTRACT.md:104`, directional ties are
grouped by adjacent sorted gaps <= `branch_tolerance`; Cartesian components
are averaged within the tied cluster (trace divided by dimension). This removes
secondary-degeneracy basis ambiguity. The private implementation agrees at
`concepts/polar/private/reference/solve.py:70`. Complex adjoints, Cartesian
conversion, response normalization, and the reciprocal-vector rather than
shifted-vector phase are also explicit in the contract. A wrong unaveraged
branch vector is not an unspecified-basis defense under this contract.

`concepts/polar/participant/TASK.md:29` says the measured starter normalizes to
0.5, but the more precise contract at
`concepts/polar/participant/workspace/CONTRACT.md:3` and scorer at
`concepts/polar/private/evaluator.py:55` specify derivative/response floors
1e-5 and 1e-6. Under those unchanged floors the actual starter mean is
**0.623899903199**, with case scores **0.5–0.748037851639**. For example,
`nacl_development_0` has derivative error **4.12880679452e-8**, derivative quality
**0.995888170156**, and mode-response quality **0.5**. This near-exact derivative
deserves high quality; forcing it back to 0.5 would amplify scientifically tiny
error. Fix the blanket wording, not the floor. Stored-reference mean is **1.0**;
all-zero output mean is **0.075980052929**. A substantive response/tie/near-Gamma
failure can be meaningful, but a scalar gap alone does not show that an analytic
derivative is necessary: accurate finite differences are explicitly allowed.

### Cubic

`concepts/cubic/participant/workspace/CONTRACT.md:36` explicitly fixes
`exp(2*pi*i*G dot (tau_a-tau_0))`, shortest-image averaging, and the three-origin
**complex amplitude** average;
`concepts/cubic/participant/workspace/CONTRACT.md:79` forbids eigenvector conjugation and fixes
the strict signed-frequency cutoff. The suspected phase convention is not
missing. The pinned private C adapter is at
`concepts/cubic/private/reference/oracle.py:58`; existing literal-average/C
crosschecks are documented in `concepts/cubic/private/reference/README.md:199`
(largest recorded relative discrepancy 1.665e-15), not rerun or rebuilt here.

Current stored-weak/reference means are exactly **0.5 / 1.0**; zero-output mean
is **0.009621292715**. The baseline raw relative errors range
**0.002532840479–0.019438381740** for reciprocal tensors and
**0.002065423141–0.018016984580** for coupling strengths. Therefore modest
absolute relative errors can noticeably lower this baseline-relative score.
Origin/image/mode-contraction failures can be meaningful, but report their raw
per-triplet errors before describing a low score as a major physics failure.
No comparable zero-output shortcut was found in this bounded check.

## 4. Narrow, ratchet-safe follow-up

1. **During these pilots:** freeze contracts, manifests, score scales, and
   acceptance criteria. Preserve current scores and this audit side by side.
   Do not inspect or alter pilot work to resolve these author-side issues.
2. **Acceptance review:** use existing raw component/family metrics, the generic
   zero baseline, and explicit reference headroom. Hold fitting acceptance if
   its case rests only on the cited >0.90/<0.70 scalar checks. Do not describe
   the privileged harmonic ablation as an achievable generic baseline. For
   grid, inspect CDF/image-set raw errors even when flat-case quality is near 1.
3. **After this run, without making the task harder:** correct the polar 0.5
   wording and publish the fitting aggregation formula. Retain the already
   explicit polar tie, cubic phase, and grid point-mass conventions; no extra
   hidden convention or new case family is justified by this audit.
4. **If score revision is authorized for a later version:** normalize fitting
   tensor accuracy and physical consistency separately so a badly unconstrained
   weak tensor cannot pay for missing fc3. Independently normalize grid CDF vs
   DOS and image-set vs distance errors before combining them. Validate against
   zeros, the measured weak outputs, and references. Any residual-only cubic
   force diagnostic must be separately labeled; reference-fc2 subtraction is
   privileged. Predeclare scales before new blinded pilots, retain old scores,
   and never tune them to force these live pilots below a threshold.
5. **Reporting only:** `author/evaluation.py:139` reports a case-weighted
   `mean_core`, whereas grid's contract promises family-balanced reporting and
   `concepts/grid/private/evaluator.py:116` provides that in its specialized
   `grid_summary`. `author/score_submission.py:40` uses the shared path without
   that grid postprocessing. Label the actual aggregate and show both from
   saved case scores; do not silently substitute a different tournament score.
   Shared “reference 1 / weak 0.5” metadata at `author/evaluation.py:213` likewise
   needs concept-specific qualification, not a live numerical change.

## Artifacts and verification

- `author/contract_audit/score_fitting_ablations.py`: reproducible scoring-only
  fitting audit, with explicitly separated generic and privileged outputs.
- `author/contract_audit/fitting_ablations.json`: 24 full fitting score records.
- `author/contract_audit/check_other_scores.py` and
  `author/contract_audit/other_scores.json`: 102 direct-score controls across
  polar/cubic/grid, raw errors, and empirical flat-CDF/threshold checks.
- `author/contract_audit/validation.json`: 12 fitting score comparisons to
  existing measurements, 12 saved-output checks, Python syntax checks, split
  means, audit-script hashes, and unchanged watched-source hashes.
- `author/contract_audit/source_hashes_before.json`: initial watched sources.
  The two `*_audit.log` files in this audit directory contain only our own
  scoring diagnostics, not model or pilot logs.

These controls establish score behavior on the current stored cases. They do
not establish a new constrained solver, runtime feasibility, an independently
recomputed reference, exhaustive absence of shortcuts, or any live pilot result.
