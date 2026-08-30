# Wall-guard patch review

Updated 2026-08-28T16:43:42.722913+00:00. Bounded static review of the **actual patch**, not a solver grade or runtime security certificate.

## Verdict

**No concrete false-pass or timer-reset escape found in the reviewed patch.** The fixed protected-worker timer and final pass predicate look sound under the existing no-descendant/memory-isolation boundary. One concrete infrastructure-classification ordering gap remains (**WG-01**); it can turn an inconclusive watchdog event into a failed scientific stage, not into a pass.

Only `authoring/wall_guard_review.md` and `.json` are written. No evaluator, participant, attempts, champions, calibration or final isolation audit is changed. No submitted program, grade, new agent or regression was executed. Main's reported four new plus six old regressions were not awaited or claimed passed.

## Reviewed bytes

| Source | Reviewed SHA-256 |
|---|---|
| `concept_1/evaluator/worker.py` | `0648a2f8dea65c7618e4cf1786a78aaa22782f845cdb0afd30a0162d16be42cf` |
| `concept_1/evaluator/sandbox_runner.py` | `2574e9053110c37788ef5a92b4b42963a2fda7f9f8e98518f0ff4b439624b8bc` |

Diffs were checked against `concept_1/adversary/wall_guard_repair/original/worker.py` and `concept_1/adversary/wall_guard_repair/original/sandbox_runner.py`; their hashes and report-write source hashes are in JSON. Sources still match at report write. In-memory AST syntax parsing passed; no evaluator/submission modules were imported or bytecode written.

## Correctly preserved invariants

- `worker.py:58`: reads wall once before spawn; the single monotonic start precedes `Popen` and is never reset. Child Python/bootstrap/import time is included, preceding trusted startup is not.
- `worker.py:63`: one exact-PID `wait4(WNOHANG)` loop, latched timeout, direct SIGKILL and reap before final accounting. Elapsed wall is captured immediately after waiting, before report I/O.
- `worker.py:52`: retains nondumpable supervisor, preopened exclusive/no-follow descriptor, close-fds, post-reap identity/link checks and final descriptor rewrite. Existing pre-submission no-fork/thread/exec and memory/FD restrictions are unchanged.
- `sandbox_runner.py:105`: fixed `120 + original wall` host watchdog, no mutable marker or resets. Successful scoring uses protected worker wall; outer wall is diagnostic.
- `sandbox_runner.py:129`: finite nonnegative CPU/wall, boolean timeout and exit-consistency checks plus clean outer exit and original limits prevent a missing/over-budget/inconsistent record from passing. An actual late exit fails the wall check even if the timeout flag is false.

## Findings and smallest remedies

**WG-01 — Confirmed classification gap, no false pass.** At `concept_1/evaluator/sandbox_runner.py:137`, a non-regular/non-single-link `stderr.log` returns `process_valid=false` before the outer-timeout/no-accounting exception at `concept_1/evaluator/sandbox_runner.py:144`. A child can replace stderr with a symlink and stop its supervisor; after the outer guard, missing final accounting then becomes a failed scored stage rather than `infrastructure_error`/`score=null`. Missing stderr likewise escapes the intended classification through an earlier filesystem exception. This is a static control-flow counterexample, **not an executed exploit**. Move the existing watchdog/no-accounting exception immediately after accounting parsing, before stderr access and early returns. The ordinary authenticated worker-timeout path must remain a resource failure.

**WG-02 — Defensive parser strictness, not an established child escape.** `float(...)` accepts numeric strings/booleans and `isinstance(worker_exitcode, int)` accepts a boolean; default JSON parsing also permits duplicate keys. For outer exit zero, CPU `"0"`, wall `false`, exitcode `false`, timeout `false` and the correct tag satisfy the parser. The actual protected final writer emits genuine numbers/integers after reaping the only child, so this does **not** demonstrate a forged passing report. If strict malformed-record rejection is required, check exact integer/non-bool numeric types before conversion and reject duplicate keys; retain the final-write/exit trust boundary.

## Tampering and liveness

The report is same-UID writable while the child runs; file existence or mode 0600 is not authentication. A successful path depends on the last trusted rewrite **after reap**, preserved inode/link identity and clean outer exit. Replacing/hiding the path invalidates; restoring the original inode still permits the trusted overwrite. Request edits cannot change already captured host/supervisor budgets. Signals can delay or invalidate the supervisor, but cannot reset its clock or manufacture its clean terminal rewrite. No new proc/memory/FD bypass was found statically; those existing barriers were not empirically probed here.

Direct-child reap rules out that child being live after the final report. No-other-untrusted-process reasoning remains conditional on the unchanged seccomp barrier. Post-kill namespace cleanup is a regression obligation, not an untested guarantee.

## Nonblocking operational caveats

- `worker.py:70` and `sandbox_runner.py:108` still use blocking reaps after SIGKILL; process construction and filesystem cleanup are not separately bounded. `120 + wall` is a watchdog trigger, not a demonstrated absolute return-time bound under uninterruptible kernel/IO stalls. This may hang/invalidate, not falsely pass. Retain an outer harness deadline and verify quiescence; incomplete accounting/cleanup cannot grant a solver result.
- `sandbox_runner.py:64` stages the child worker, while `sandbox_runner.py:47` rereads live supervisor source. Keep paired edits quiescent; optionally bootstrap from that same staged copy to avoid mixed revisions. Existing runs need their own source hashes.

## Focused regression expectations — not run here

1. Trusted pre-spawn delay versus child bootstrap delay: only the latter consumes worker wall.
2. Low-CPU sleep/SIGSTOP and deadline races: kill/reap and no actual over-budget pass.
3. CPU burner versus short normal child: real child CPU and original limits remain authoritative.
4. Mutable request/resource tampering: no deadline resets or forged terminal success.
5. Supervisor stop with missing/forged accounting plus malformed stderr: no pass; no authoritative accounting means null-score infrastructure (WG-01).
6. Proc/FD/raw process creation and setsid variants: isolation holds and cleanup leaves no untrusted actor.
7. Malformed/legacy/nonfinite/negative/inconsistent records fail closed; WG-02 type strictness is optional defense-in-depth unless explicitly promised.

The JSON records exact evidence, assumptions, source identities and scope. This review does not assess hardness or scientific scores.

## Quiescent bookkeeping follow-up

Both corrected infra2 reports are now complete and valid: v1 **99.695452828125**, v2 **99.776330515625**, each 16/16 valid outputs. Generation 0 is archived at `concept_1/generations/generation_0`; the byte-identical complete v2 submission is promoted to `concept_1/champions/generation_1/submission`. No grade or sandbox regression was rerun by this sidecar.

Main accepted WG-01 and the staged-bootstrap coherence change for the next **infrastructure-only** revision after grades/archive quiesce. Test missing/symlink/nonregular stderr under an unaccounted outer timeout, preserve genuine worker-timeout failures, and confirm both worker paths use the staged bytes. These changes are **not applied here**. No participant, physical case, calibration energy or numeric target changes; scientific ratchet count remains zero and no hardness is claimed.
