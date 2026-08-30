# Pending generation 1: independently shifted phonon branches

Status: proposed for parent review only. No active participant/evaluator/status file is changed, no new fresh runner is launched, and no original numerical contract is rewritten.

## Selection and evidence

The original fresh trials both solve the original 1.12 task at effectively identical scores. The exact higher unrounded result (v2, 1.1245411788778297) and its frozen submission, launch manifest, and evaluations are archived in `../../champions/generation_1`. Its original-control replay reproduces that score. The two passing n=8 pool alternatives and the constant-total-row anticorrelated case are also solved by the actual search; these are not hardness evidence.

The selected input is `robustness_exploration/candidates/middle_cross_45`. It retains the original n=8 constraint arrays, three modes, bounds, and solver conventions; it adds the positive branch scenario `(4,100,45)` meV to the three original spectra. This is a minimax change, not a dimension, path, label, invalid-input, or formula-implementation trap. The original row profiles remain; the unsuccessful anticorrelated exploration is not concealed.

| Measured quantity | Ratio |
|---|---:|
| Private independently audited witness | 1.094955838159416 |
| Target fixed from private evidence before replay | 1.09 |
| Actual champion, original compressed-family setting | 1.0741927523646932 |
| Best actual search over every public family setting | 1.082574580261811 |
| Stronger oracle recombining all 16 produced endpoints | 1.0877026333364312 |

The oracle artifact is admissible, converged, and independently audited. Its target shortfall is 0.0022973666635688; the private/oracle gap is 0.007253204822984749. The private target margin is 0.004955838159416. The target follows the predeclared private-only rule: largest 0.01-spaced ratio at least 0.003 below a private witnessed score, requiring at least 1.08. It is not increased after observing the champion. Selection over a private pool is adversarial task design, not a statistical generalization claim.

The private solution balances two active worst-case constraints: compressed-spectrum ratio 1.094955838159416 and independently shifted ratio 1.0949561065713225. This establishes competing spectral objectives; it does not prove multiple difficult local minima or global optimality. The milder `middle_cross_60` and the other retained cases are honestly recorded as solved. `middle_cross_35` also defeats the oracle but misses its target much more narrowly, so it is not selected.

## Actual-method replay and resources

`champion_adapter/path_only.diff` changes only the public participant path; an AST check establishes that the algorithm is unchanged. Each family uses the recorded `--count 48 --starts 24` search and `--count 192 --starts 0 --resume ...` refinement. There is no literal success-ratio stop in v2; its stationarity tolerances are not target thresholds and remain untouched. All public `--family` configurations are granted, then all output endpoints may be combined. The strongest resulting pair is checked independently. Thus a stale path, family default, target, or dimension cannot explain the gap.

`family_oracle/middle_cross_45/summary.json`, `family_oracle_summary.json`, and `champion_replays/oracle_middle_cross_45__*/` preserve artifacts, logs, GNU-time CPU/wall/RSS measurements, and audits. The replay uses bwrap with only public input/code and a fresh writable output; no hidden witness is mounted. A prior sandbox-startup failure was retried and is not counted as an optimization failure. `explore_robustness.py`, `family_oracle.py`, `replay_champion.py`, and the original pool generator preserve reproducibility. `prepare_pending.py` assembles this draft; `validate_pending.py` verifies it without launching a fresh model.

## Scientific interpretation and limits

The same per-mode labeled rows guarantee the complete normal-state functions agree within each scenario; the same full static aggregate rules out a static Perron-eigenvalue score. All entries, frequencies, and spectral weights are nonnegative, and coupling bounds are unchanged. Frequency branches are fixed labels, not an energy-sorted indexing convention. The enlarged shifts are alternative effective models, not realistic isotope perturbations or an ab initio material claim.

This is a changed robustness task with a lower ratio target than generation 0, not a mathematically nested feasible-set strengthening of its success condition. The empirical requirement is an admissible actual-method failure and a private audited pass. A minimax-aware search can improve the champion, and a new fresh model may solve this quickly; there is no unsupported hardness guarantee. The finite Matsubara operators and drift tests are the numerical contract, not interval certification of the infinite-cutoff limit. The n=8 public draft is distinct from the larger private follow-up; see the subsequent shortcut evidence.

## Additional shortcut evidence: not recommended as a hard ratchet

After the full draft validated, `mixing_sanity_probe.py` tested a new two-parameter algorithm: independently interpolate the low and high endpoints between the compressed-spectrum and independently shifted-family champion outputs. A 41-point grid for each parameter, caching single-kernel transitions at M=48, finds a pair with independently audited score **1.094290457685765**, above the unchanged 1.09 target. The full probe, including final audit, takes **8.621409096999999 CPU seconds**; the selected high/low independent-family fractions are 0.875 and 0.575.

This is not the unchanged champion method, so it does not invalidate the actual replay gap. It does demonstrate that a simple small-dimensional extension solves the proposed task. The validated n=8 draft is therefore **not recommended as strong hardness evidence**. A separate bounded, nonidentical 24-patch planted-instance investigation is stored under `large_patch_probe/`; its outcome must be assessed independently. No target is raised to evade this shortcut and no active package is changed.

## Reporting-only change

The pending evaluator's numerical physics, artifact guards, signed-frequency assembly, regular-row control, and old-case validity logic are byte-identical to the frozen originals. The reporting wrapper adds a reason on every outcome, explicitly defines `core_score = worst_family_score = score`, and measures evaluator CPU/wall/peak RSS. `reporting_only/REPORTING_REGRESSION.json` demonstrates unchanged original baseline/champion scores and verdicts. Archived old outputs remain untouched. The selected new input/target is a separate, explicit numerical task change, not part of this formatting fix.

Only the parent may promote this draft or launch a new fresh attempt. Private artifacts and this decision record must not enter the participant mount.
