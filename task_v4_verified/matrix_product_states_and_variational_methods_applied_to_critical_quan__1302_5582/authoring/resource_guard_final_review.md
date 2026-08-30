# Final resource-guard review — infra5

Reviewed 2026-08-28T18:45:49.768066+00:00. **Strict solver eligibility remains CPU <= 6/40 seconds and worker wall <= 30/120 seconds. Kernel enforcement grace is not scoring grace.** No concrete false-pass path was found in this bounded static review under the preserved protected-supervisor/no-descendant boundary.

## Freeze and scope

- Worker SHA-256: `f634e57b2852b0fcfe0811a1dc3530daacd2085c9eb3062da06d1c9dd4eb5854`.
- Runner SHA-256: `f6d0c8edea952a75fa43446860c57bdfbe972afa51e157659390f21d4ece56bd`.
- All six source pins in `concept_1/adversary/wall_guard_repair/freeze_manifest_v5.json` match; the certificate records 15 passed checks.
- `concept_1/adversary/ratchet_1_admission/freeze_manifest.json` matches all 26 reviewed fixed-source/public pins and the complete 16-file public surface; no public symlink or bytecode is present.
- No runtime tests, grades, admissions or new scientific queries were executed. No ongoing A v3/v4 artifacts were read. Only these two review reports are written in this phase.

## Success predicate

`worker.py:46` adds **+2/+3 seconds only to child kernel soft/hard guards**; `sandbox_runner.py:90` uses **+4/+5** for the trusted outer guard. At `sandbox_runner.py:140`, a pass still requires clean outer exit, no timeout, valid protected accounting, and measured child CPU/wall within the unchanged original request budgets. The diagnostic CPU fallback of zero cannot pass because accounting remains invalid.

`worker.py:58` captures the wall budget and monotonic start before child spawn. `worker.py:64` installs a SIGALRM handler that latches timeout and kills the direct child, then uses one **blocking wait4**. The remaining-time alarm cannot silently disable itself when startup consumes the budget. Reaping precedes inode/link validation and the final report rewrite. Actual elapsed time over the wall cap rejects even if the timeout flag is false. Trusted supervisor wait4 polling is gone; the host now uses `Popen.wait` with its operational watchdog.

## Prior findings closed

- **WG-01:** `sandbox_runner.py:129` now aborts an unaccounted outer timeout as infrastructure **before** any stderr access or early return. Malformed stderr no longer converts this path into a scientific stage failure.
- **Staged coherence:** `sandbox_runner.py:47` reads bootstrap bytes from the same staged worker file mounted for the child, not live evaluator source.
- **Trusted polling overhead:** the protected supervisor no longer spends CPU repeatedly collecting rusage while waiting.

## Recorded regression evidence

The pinned infra5 certificate records **6 runner + 4 wall + 4 classification/coherence + 1 normal-exit CPU checks = 15**. The source of `test_cpu_eligibility.py:12` explicitly requires a normal zero exit, authenticated CPU above its 1-second test budget, no timeout, and rejection. Its 2-second CPU workload stays within kernel grace; the strict final CPU gate still rejects it. These are the main's recorded checks and reviewed sources, **not tests rerun by this sidecar**, and are not fresh scientific grades.

The preserved **39.341316 CPU / 40-second budget SIGXCPU** event is marked excluded from hardness in the infra5 certificate. The user-reported trusted-parent polling episode (4.502 seconds system CPU in 6.547 seconds wall) is likewise infrastructure evidence, not solver hardness. Neither event authorizes accepting a currently signaled, over-budget or unaccounted solver.

## Remaining assurance limits

The accounting file is not itself secret or immutable while the child lives. Its authority comes from the protected last rewrite after reap, identity/link checks, clean outer exit and the unchanged no-process/no-thread/exec/memory-escape restrictions. Signaling can cause invalidation or DoS, not a clean authenticated pass. Numeric coercions/boolean integer aliases remain defensive schema caveats, not an established false-pass exploit on that terminal-write path.

The host watchdog is operational rather than an absolute end-to-end guarantee: process construction, blocking post-kill waits and filesystem cleanup can still stall. No missing-accounting fallback is eligible to pass. Kernel containment and all runtime races are not independently re-attested here.

The separate isolation extension remains pending both A v3/v4 completions. The original 11-run audit is preserved; **this report does not claim 13 completed attempts**.

## Completed isolation extension

Update 2026-08-28T19:41:58.289267+00:00: the earlier pending-completion note is superseded. A v3 and v4 completed voluntarily in 2944.589869573014 and 3342.3605917230016 seconds, respectively, both return 0 without timeout. `authoring/final_isolation_audit_v2.json:1` now covers all thirteen completed runs, with status `verified_with_documented_historical_and_attestation_limits` and retained historical/attestation caveats. No grading result or hardness inference is part of that conclusion.

## Separate CPU-overshoot follow-up

Update 2026-08-28T19:51:08.577710+00:00, after completion of the thirteen-run isolation audit. Main reports authenticated short CPU totals **7.117149** and **17.117624** against CPU6, the latter with outer exit137. No grade was reread or rerun by this follow-up, and no ongoing v4 grading artifact was opened.

**Static attribution remains incomplete.** `worker.py` starts the solver interpreter and performs trusted module initialization before lowering the child's CPU guard to soft8/hard9; its final wait4 total includes that child initialization, user imports/computation, native calls and state output. The protected supervisor and outer bwrap CPU are not part of this direct-child total. However, the child should already inherit the outer short guard of soft10/hard11, so pre-setter startup alone does not establish why the total reached17.117624. The repeated near-.117 fractional component is not evidence of a particular phase.

The completed v3 source uses CPU origin0 and a0.60-second reserve, then cooperative native-loop checks and an unclocked final np.savez/write. Those paths can explain a modest voluntary-budget overrun in principle; they do **not** establish an exemption from the kernel hard9 guard. No cap/signal/process manipulation appeared in the five inspected production text files; the native binary was not executed or attested against its C source. Exit137 alone also does not identify wall-kill versus another termination path: the protected child exit status and timeout flag matter.

7.117149 exceeds the unchanged CPU6 eligibility threshold, so rejection is consistent with the strict predicate.17.117624 is also over budget but its unexpectedly high guard overshoot is unresolved. Neither number alone proves an infrastructure false failure; neither should support a scientific-hardness claim. The earlier39.341316/40 underbudget SIGXCPU exclusion remains a distinct event.

**Proposed, not executed:** after grading quiesces and with explicit authorization, use an isolated private instrumented copy for at most three diagnostic processes: the two already reported failed short requests with unchanged v3, plus one startup-only control. Preserve CPU6/wall30 and all existing kernel/host guards. Record child user/system CPU and inherited limits at the earliest practical trusted marker, before/after RLIMIT lowering, and immediately before runpy; record final wait4 user/system separately, exact child status/timeout, and separate parent CPU. Protect phase data in the nondumpable parent via a bounded pre-user pipe, closing child descriptors before user code; do not reintroduce polling or mutable-marker authority. Missing phase data is inconclusive.

These measurements would distinguish initialization cost from later user/import/output work without editing frozen sources or performing an official regrade. No retries, score subtraction, target relaxation, fresh agents or runtime diagnostics are authorized by this review itself. The two isolation-v2 reports remain unchanged.
