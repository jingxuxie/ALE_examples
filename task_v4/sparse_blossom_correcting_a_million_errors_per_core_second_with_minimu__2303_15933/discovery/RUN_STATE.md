# Session complete, 2026-08-28

All fifteen scientific fresh-agent attempts and all eight task generations are
complete. Final decisions are recorded in `../status.json` and `../REPORT.md`.
Concept 1 generation 2 is the selected `hard_open_candidate`; concept 2 generation
3 is another open candidate. Neither has a known passing final solution. Concept
3 generation 3 is solved by both fresh agents; the best is preserved in
`../concept_3/champions/generation_3/`. Its two final mean/worst log-RMSE results are
0.056575/0.075526 and 0.056298/0.073771. No fresh run or builder remains pending.
The final package audit and consistency assertions pass. The checkpoint below is
historical and is superseded by those final records.

## Historical checkpoint, approximately 19:30 UTC

This is a generation-only checkpoint, never participant input. The user requests
three concepts in three modes, one genuinely hard retained task, independent
one-hour ultima-alpha attempts, and at most three champion generations per
concept. Final reply must contain only concepts/modes, baseline/champion and
fresh scores, counterexample searches, ratchet counts, statuses, solvability,
and failed substantive capabilities.

## Runtime and tools

- ROOT is this task's parent directory; `/home/.../ALE` and `/srv/home/.../ALE`
  are the same inode. Current working directory is the `/srv/home` alias.
- Persistent sandboxed shell is tool session `13991`, with shell variable ROOT.
- Mandatory bwrap evaluators A/E require an escalated outer exec. Never remove
  isolation. B only reads a bounded JSON artifact and needs no escalation.
- Private launch wrapper: `discovery/run_attempt.py`; scorer/freezer:
  `discovery/finish_attempt.py`. Model ultima-alpha, high effort, 3600 seconds.
- Targets, participant and evaluator are immutable after each fresh launch.
- `audit_packages.py` verifies completed-launch hashes and package structure.
  `collect_results.py` creates a raw tournament metric index, not decisions.
- All completed submissions have pristine pre-evaluation snapshots. E runs a
  separate evaluation copy so hidden observation caches never reach champions.

## Concept A: decoder baseline improvement

Initial generation solved: 1523/12288 baseline errors versus 153 fresh errors,
89.954% reduction, 96.376 CPU seconds. Actual champion promoted to
`concept_1/champions/generation_1`.

Generation 2 frozen target: 20% pooled and 15% holdout reduction, no family
regression, positive paired CI, 132 CPU seconds, one process/thread, 6 GiB.
Baseline: 427/3072 failures (family counts 108/113/206), 107.964 CPU seconds.
Private sweeps: stronger ensembles give only 5.94% at 4.65x CPU; no qualified
passing solution. If fresh attempts fail, status is hard_open_candidate.

- Gen2 v1 reached its coding deadline; intact runnable artifact evaluated valid.
  389 errors, 8.8993% reduction, worst-family reduction 0, holdout 11.1628%,
  CPU126.106975, all resource gates pass. Relative95% CI [.04020,.13779], below
  20% target. No mutation before/after evaluation. A substantial quality miss.
- Gen2 v2 still running: CLI session59919, scorer80254. Its deadline is around
  19:43UTC. Initial v1 CLI84888/scorer34979 have finished.
- Builder Linnaeus `01a04917-ca0e-7823-aec7-b7482361af65` is closed; resume only
  if v2 actually passes and a final generation3 is required.

## Concept B: robust entropy-inversion witness

Gen1 two fresh passes: 1.0089286233 and1.0089298998. Gen2 two fresh passes:
1.0104109012 and1.0104079400. Threshold is1, not probability. Best actual
gen2v1 is `concept_2/champions/generation_2/witness.json`.

Final gen3 is frozen: 131 explicit continuous 1-D calibration paths, including
43 orientation-conditioned directions at the same +/-5% local magnitude.
Targets unchanged: global gap1.08/posterior.85/mass1.75e-5; local .85/.845/1.75e-5.
Not a full calibration box. Champion score .9197899012, nine actual failing
paths and five additional certificate-only failures. Exact point minima gap
.8053940642 and posterior .8418515011. Private best .9652626095; no passing
witness known and no impossibility proof. Gen3 is hard-open if both fresh fail.

- Audit:5791 independent comparisons,258 off-anchor,129 reflection,40 malformed.
  Independent full-state checker takes about887CPU/960wall seconds,69MiB. Its
  nominal900wall allowance does NOT invalidate an artifact; no submitted code.
- Both final fresh attempts started18:41:19UTC, deadline19:41:19UTC.
  CLI sessions88775/62044; auto-freeze/scorers83888/29112.
- Latest public search reports around .97718, still below1; await official
  scoring. Inspect actual-versus-certificate-only failures before claiming
  substantive robustness failure. Do not change certificates after launch.
- Builder Aquinas `01a04918-0bdb-7142-a88a-e2dc38a12994` is closed. This is the
  final planned B generation (initial plus two ratchets).

## Concept E: active correlated calibration

Original generation's first fresh policy failed .055933/.133077 mean/worst
against .055/.095, but passed three new noise tapes; four-tape pooled diagnostic
is .051174/.087479. Second independent fresh policy passed .050292/.089073.
Therefore original generation is SOLVED, not retained on a noisy outlier.
Actual v2 champion is `concept_3/champions/generation_1`.

Gen2: connected all-active14–20 detector graphs,43–77 local channels,40k shots,
64queries,max4000/query,60CPU,3GiB. Targets .075mean/.125worst fixed before
policy trials. Weak baseline .105738/.166973; uniform local-composite control
.089878/.133301. Private static, adaptive and robust policies pass; robust
.063411/.088417 at5.201CPU. Original dense champion fails CPU atD14 and memory
atD16–20, with sanity/protocol controls and unchanged source hashes.

BOTH gen2 fresh agents pass:
- v1 .05015128124106103 mean, .062246142645026925 worst, maxCPU26.083223,
  elapsed2069.9334 seconds. Source has88files. This is the FINAL BEST champion.
- v2 .05070591488203297 mean, .0696393406690843 worst, maxCPU20.329711,
  elapsed1460.9190 seconds. Source has106files; it was provisionally promoted.
- Best v1 exact source is now `concept_3/champions/generation_2`; selection and
  metrics are sibling JSON files. v2 preserved under
  `adversary/provisional_champions/generation_2_v2` with sibling metadata.
- CLI22177/31039 and scorers52266/62720 have completed.

Builder Peirce `01a04918-908f-7201-a9c3-0acbb24792f0` is ACTIVE preparing final
E generation3. Scope: `concept_3/adversary/final_scaling_preparation` and new
`concept_3/generations/generation_3`. He must stress ACTUAL BEST v1, not former
provisional v2. Main has authorized sealing after scientific validation and
fixed-target/portfolio qualification; no need to wait for selection anymore.
He must not launch fresh agents or modify frozen generations/root status.

Preparation explores larger connected all-active local graphs D28–44, with
same degree/support and observation law. Include D24/D28 controls to distinguish
representation/information/resource failure from32-bit handling bugs. Actual
v1 may use low-dimensional parity projection; verify source and real failures,
do not assume. Preserve complete actual champion source, runnable weak baseline,
private passing policy when available. No diagnosis/algorithm prescriptions in
TASK. Do not invent feasibility or freeze an unjustified target. This will be
the final E generation (initial plus two ratchets).

## Remaining work

1. Await A gen2v2 and B gen3v1/v2; evaluate and adjudicate genuine failures.
2. Audit E gen3 READY, exact best-champion identity, frozen files, baseline,
   resource accounting, scientific validity; launch two independent fresh
   attempts with the same wrappers and one-hour limits, then score.
3. If A gen2v2 passes, promote actual best and privately investigate a final
   A generation3 rather than suppressing the success.
4. Update root/concept/generation statuses from official results. Root E and
   its gen2 status still need to reflect both gen2 passes and active gen3.
5. Final package audit, raw score collection, root status.json and REPORT.md,
   choose the strongest retained task, report only the user's requested fields.
6. Close builder agents when done. Do not commit, add branches, alter frozen
   tests, count infrastructure-start failures, or claim old-generation
   feasibility for an open later generation.

Two initial B preflight launches blocked on inherited stdin and were archived
as infrastructure exclusions before any code output. Wrapper stdin is now
DEVNULL. The normal 'Reading additional input from stdin...' banner alone does
not imply a failure. Original A CPU-meter and Fortran-buffer exploratory bugs
were fixed before corresponding fresh tasks and invalid old reports excluded.

## Superseding checkpoint, approximately 19:53 UTC

- A gen2v2 reached3600.58sec and its official evaluator failed rc137/SIGKILL:
  CPU128.805497, wall403.4615, RSS114300KiB, no watchdog, empty worker log.
  Do NOT assert proven132CPU overrun from this alone. Linnaeus is resumed for
  bounded diagnosis ONLY in `concept_1/adversary/second_attempt_diagnostic`:
  one unchanged official replay and one isolated relaxed-ceiling diagnostic,
  no frozen/source/status edits. Await cause and quality evidence. v1 remains
  a substantial valid8.9%-versus20% quality miss.
- B gen3v1 ended at19:41:19UTC by deadline; v2 ended normally19:41:04UTC.
  Both independent scorers83888/29112 are running (roughly15min each).
- E gen3 READY and independently audited:105 sealed files, all88 actual best
  v1 champion files identical. Targets .090mean/.140worst,28–44detectors,
  88–179channels, same40k/64queries/60CPU/3GiB. Private robust passes
  .070182/.113583 at25.575CPU; uniform .104358/.159844, weak .133674/.210986
  fail. Actual v1 fails D24/D28 allocation before any integer-width boundary.
- Final E gen3 fresh attempts launched around19:50UTC. CLI sessions6079/75546;
  auto-freeze/scorers43046/82132. Read launch.json for exact deadlines. This is
  FINAL E generation. Builder Peirce is closed, no further generation needed.
- All E generation2 scores/selection and root E active-generation metadata are
  updated. E gen3/status.json still needs fresh-running metadata, later final
  results. Root E ratchet count needs2 after this final generation.
- Root final status.json/REPORT.md and final per-concept latest-generation
  statuses are not yet written. Complete audits and raw score collection first.
