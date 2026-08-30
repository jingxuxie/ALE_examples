# Generation 1: bounded static failure hypotheses

**Private authoring notes, August 28, 2026. Not empirical counterexamples.** Main reports the completed champion passed the official frozen suite at mean NRMSE `0.0359657`, worst-family `0.0571207`, with 32/32 valid episodes. This review only read source; it neither imported nor executed the champion, inspected the running sweep's results, nor changed scientific assets. Main alone owns search execution and any ratchet.

Reviewed `champions/generation_1/solution.py`, SHA-256 `73e7249f992748fe85090068a79deba7e81b6665bd2da283ee477dacf86f79ff`. References below are relative to `concept_3`. The search script remains frozen at SHA-256 `01d15c2074606c7e111a20588a9f1f0ba0398d7f2a6c9005bd473a19e130ca78`.

## 1. Local-mode commitment after the short bootstrap

- **Source:** `champions/generation_1/solution.py:163`, `champions/generation_1/solution.py:182`, `champions/generation_1/solution.py:240`, and `champions/generation_1/solution.py:210`. Bootstrap durations stop at 0.97; the initial derivative-based guess uses time 0.15. Five starts are that guess plus four nearby Gaussian perturbations. Subsequent phases refit from one estimate and allocate using Fisher curvature at that same point, rather than an ensemble of competing modes.
- **Hypothesis:** a noisy or nonlinear bootstrap can select an incorrect conditional-frequency/axis basin, after which locally efficient experiments fail to discriminate alternatives. The final batch spends 9,216 shots before its next refit. High-frequency or nearly coincident conditional rotations are plausible stress regimes, not demonstrated failures.
- **Discriminant:** stable wrong estimates or conditional-frequency/ZI offsets across fresh noise seeds, with full budgets and comfortable solver time, would support a wrong-mode hypothesis. Inconsistent errors that match a local precision scale would not. Full-rank local curvature alone cannot distinguish a correct mode from an incorrect local basin.

## 2. Early nuisance-regime selection is never reconsidered

- **Source:** `champions/generation_1/solution.py:173`, `champions/generation_1/solution.py:196`, and `champions/generation_1/solution.py:261`. An amplitude threshold proposes a nuisance box, then the alternative box receives one fit. The lower-cost choice is retained through every adaptive phase. The alternative-box expression correctly switches regimes; it is not an inverted-condition bug.
- **Hypothesis:** insufficient early separation, compounded by a local fit in the alternate regime, can select a box excluding the true visibility/contrast/decay and force Hamiltonian coefficients to compensate. The initial regime gets multiple starts; the alternate gets one. This is a conditional risk, not evidence that misclassification is common: the public boxes are well separated and the code explicitly compares both.
- **Discriminant:** consistent high-error points near nuisance-box edges warrant checking which box was retained. A one-off threshold mistake disappearing under the three fresh seeds is not a suitable ratchet case. Existing sidecar outputs do not expose internal nuisance estimates or the selected box; attribution would need separately authorized sandboxed instrumentation, not inference from the family label alone.

## 3. Center-shrinkage bias at nuisance boundaries

- **Source:** `champions/generation_1/solution.py:122`, `champions/generation_1/solution.py:145`, `champions/generation_1/solution.py:215`, and `champions/generation_1/solution.py:273`. Allocation adds a nuisance information prior, and the final fit penalizes departure from each nuisance interval's midpoint with weight `sqrt(12)/width`. This is Gaussian-style, moment-matched shrinkage; the actual within-family nuisance law is uniform on a bounded interval.
- **Hypothesis:** genuine boundary values can be systematically pulled toward the midpoint, while Hamiltonian coefficients compensate through nuisance correlations. Using that prior in both allocation and final fitting can reduce the measurements that would challenge the shrinkage assumption. The effect could matter for large decay, low visibility, or extreme bias; it may also be too small to matter at this shot budget.
- **Discriminant:** consistent signed coefficient bias, rather than merely large spread, across independent seeds and neighboring parameter points would be suggestive. Any later comparison with an unregularized fit must use the same observations and remain a separately authorized private diagnostic. A family aggregate or one tail observation does not establish prior-induced bias.

## 4. Restricted candidate set and batch-level adaptation

- **Source:** `champions/generation_1/solution.py:203`, `champions/generation_1/solution.py:223`, and `champions/generation_1/solution.py:266`. Candidate times come from fixed phase-seeded grids; control preparations omit `X-` and `Y-`. All target signs and all nonidentity Pauli measurements are included. Durations expand in three stages, and blocks of 128/192/256 shots are allocated without updating the estimate within a stage.
- **Hypothesis:** a locally preferred subset may inadequately separate bias, axes, or weak entangling directions when the current estimate is inaccurate. This is a possible robustness/efficiency limitation, **not** a claim of an exact timing alias, absent phase anchors, or fundamental nonidentifiability. The candidate pool is broad, and sign-related experiments may already supply much of the missing information.
- **Discriminant:** poor information under the champion's actual selected design at the true parameters, with available in-budget alternatives improving the relevant directions, would support a design limitation. The sidecar's Fisher audit uses the fixed baseline schedule, not the champion's transcript, so it cannot establish that comparison by itself. Keep this lower priority unless repeat data suggest a design-specific weakness.

## 5. Time guards can look like calibration failures

- **Source:** `champions/generation_1/solution.py:137`, `champions/generation_1/solution.py:259`, and `champions/generation_1/solution.py:267`. Multistarts stop after five wall seconds; later phases can stop after thirteen wall seconds or twelve process-CPU seconds. Fitting raises at 16.3 wall seconds or 15.5 process-CPU seconds. The exception handler returns the last completed estimate. A timed-out refit can therefore discard newly collected observations even after spending the full shot budget.
- **Hypothesis:** parallel-host contention or unusually costly fits can produce a valid but stale estimate, rather than an intrinsic scientific failure. Guard-induced shot totals can be 5,120, 9,216, or 15,360; full 24,576-shot consumption does not prove the last fit completed.
- **Discriminant:** compare solver wall time, shots, queries, and a main-authorized lower-concurrency replay before promoting such cases. Parent-observed `cpu_seconds` may omit namespace descendants and should not diagnose the champion's internal CPU guard. A failure disappearing with reduced contention is not evidence for a harder physical calibration regime.

## Evidence gate before any ratchet

1. Keep the selecting screening count out of the repeat statistic. The scheduled three fresh measurement seeds are useful initial evidence, not proof against noise-only selection. The search's 0.09 cutoff is a diagnostic borrowed from a family-mean threshold, **not an existing per-episode pass requirement**.
2. Separate stable signed bias/wrong modes from variance, protocol/resource failures, and startup infrastructure errors. Repeated nuisance-family error alone may reflect an ordinary information limit.
3. Treat fixed-schedule Fisher flags as design-specific, local, unbiased diagnostics. Neither a large bound nor full rank proves what an adaptive controller can achieve; the bound is not a global or Bayesian impossibility result.
4. For only a few strongest candidate clusters, main can authorize additional held-out noise seeds and nearby fresh parameter draws before freezing any next-generation cases. Do not preserve a favorable screening noise seed or infer a mechanism from the cluster label alone.
5. Keep the exact public physics, trusted phase anchors, positive SPAM contrasts, and valid budgets. Do not change the current task, generator, or target. Any future ratchet requires main's empirical decision and a separately frozen generation; target achievability must remain explicit.

No unitary, tensor-order, or analytic-derivative defect is established by this static review. The champion's README reports its own numerical checks; this authoring pass did not independently execute those checks. Intermediate optimizer states, nuisance estimates, and experiment traces are not saved by the current sidecar, so several causal hypotheses remain intentionally unresolved.
