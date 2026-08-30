# Checker repair 2: concept solved

Recorded 2026-08-28T07:43:41.037665+00:00. This is an authorized evaluator repair, not a task ratchet.
No new fresh session was launched. All original reports and champion archives remain intact.

| Unchanged submission | Core | Worst family | Support F1 | Strength error | Mean / max CPU (s) | Max wall (s) | Pass |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Champion | 1.000 | 1.000 | 1.000 | 2.19e-09 | 14.282 / 48.261 | 48.456 | Yes |
| Uniform baseline | 0.667 | 0.500 | 0.884 | 0.224 | 11.120 / 14.202 | 28.595 | No |

All 24 episodes have complete final kernel wait4 accounting and valid protocols.
The champion has exact support and vortex configuration on all 12 scenes. The
baseline's reconstruction metrics exactly match its historical full-suite result.
Both were graded against the unchanged original absolute target, not each other.

- `champion_full12.json`, `baseline_full12.json`: repaired complete private suites.
- `resource_tests_release.json`, `validation_release.txt`: 30 passing checks in 21.262 seconds.
- `independent_validation.json`: all 24 case draws, independent BdG/resolvent LDOS,
  observations, metrics, resource limits, and protected asset checks pass.
- `resource_audit.json`: exact resource evidence, scope and known limitations.
- `status_before_repair.json`: original root status retained before the solved update.
- `../../evaluator/hidden/checker_revision_2.json`: current checker integrity manifest;
  the original generation-one freeze remains unchanged historical evidence.
- `../../evaluator/RESOURCE_ACCOUNTING.md`: reaper, sampler, syscall safeguards,
  complete versus forced-kill accounting, and precision limits.

The production fix uses an evaluator-local subclass of the unchanged shared
Sandbox, a trusted namespace reaper, final wait4, and a live whole-tree sampler.
It removes the per-process CPU grace (strict 90/90 RLIMIT), checks aggregate CPU
at 90, and retains the independent 120-second wall cap. No hidden state enters
the submitted process; the added read-only guard is standalone and contains no
physics, private seeds, or labels. Ordinary fork/thread/NumPy and scratch
compilation tests pass.

Short-budget busy/fork tests stop on confirmed aggregate CPU; short-lived reaped
children, orphans, and nonleader-thread forks are counted. A deliberately disabled
live sampling test still rejects excessive final CPU. Historical CPU values are
not retroactively rewritten: they undercounted the solver on this host.

Development test failures are retained for audit. Their fixed startup/idle CPU
assumptions varied with host throughput; the final checks use actual one-core
CPU/wall invariants and a synthetic no-double-count transfer test. No production
limits or scientific quality gates were relaxed. Live stopping has tick/polling
latency; forced-kill totals are not claimed complete. See the resource audit for
remaining platform and syscall compatibility limits.

The prior broad champion challenge is unchanged in `../../adversary/ratchet_1/`.
It did not establish stable scientific counterexamples; no harder generation
was created from throughput artifacts. Concept 3 remains generation 1, solved.
