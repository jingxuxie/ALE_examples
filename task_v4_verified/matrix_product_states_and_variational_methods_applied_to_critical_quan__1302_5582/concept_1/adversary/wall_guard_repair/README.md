# Resource-accounting correction

The initial optimizer reports gave quality 1 on every completed stage. Each
fresh submission lost one short stage to the host's 30-second outer bubblewrap
watchdog. Those incomplete runs had no protected solver accounting. They are
not evidence of scientific difficulty and are retained as raw, inconclusive
reports rather than silently overwritten.

Revision 2 starts the declared wall clock in the protected supervisor immediately
before launching the fresh solver interpreter. It includes that interpreter's
startup, restrictions, imports and user code, and ends after direct-child reaping.
The supervisor enforces the same 30/120-second limits. The host separately allows
120 seconds for trusted launcher overhead; this allowance cannot increase the
solver's declared budget. A host watchdog failure without protected accounting
aborts the evaluation as infrastructure failure rather than assigning a score.

The existing direct-child CPU accounting, CPU limits, memory/file limits, network
and process isolation, and protected report-inode checks remain in force. The
host now checks the supervisor's wall time, timeout flag and exit status as well.
No participant asset, physical case, variational reference energy/state, scoring
formula, or numeric target changes. This is not a champion-ratchet generation.

`test_wall_guard.py` distinguishes a delayed trusted launcher from a sleeping
solver and tests report forgery and report replacement. Existing sandbox tests
cover CPU exhaustion, isolation, network/process denial, symlinks and malformed
artifacts. `finalize_revision.py` refuses unrelated frozen-file changes and emits
the old/new calibration hashes. The original infrastructure, calibration and raw
fresh reports are preserved. Regrading uses unchanged fresh submission bytes.

Both corrected fresh reports pass all 16 stages with quality 1: v1 scores
99.695452828125 and v2 scores 99.776330515625. Their exact graded revision is
archived in `generations/generation_0/`, and v2 is the first champion.

Revision 3 addresses the independent static review's WG-01: the inconclusive
outer-timeout exception now precedes all stderr inspection, including missing or
linked stderr. It also reads the supervisor bootstrap from the same staged worker
as the child. Four focused classification/coherence checks supplement the ten
runtime/security checks. The successful scoring predicate, physical problem and
target are unchanged; the existing successful grades remain explicitly tagged
as revision 2 rather than being relabeled. `freeze_manifest_v3.json` records the
narrow follow-up and preserved archived calibration.

Revision 4 precedes every generation-1 fresh run. A public-baseline smoke test
ended without protected accounting. An instrumented identical replay passed in
5.818929 solver CPU seconds, while the trusted polling supervisor itself used
4.502154 system CPU seconds. That exposed a trusted-overhead hazard near its
inherited CPU limit; the unaccounted event is excluded from hardness evidence.
The supervisor now uses blocking direct-child `wait4` and an `ITIMER_REAL` wall
alarm. The outer watchdog uses `Popen.wait(timeout=...)`, not repeated resource
collection. The solver's original CPU/wall limits and final pass predicate remain
unchanged. Missing accounting never gives an eligible result; its zero fallback
CPU is not an estimate of solver work. Prior sources are preserved in `infra3/`.

Fourteen updated containment/timing tests pass, including an explicit requirement
that CPU exhaustion still yields protected accounting. All three new public
baseline smoke cases pass, and all eight proposed reference states are separately
remeasured. `freeze_manifest_v4.json` records the tested source identities. The
generation-1 calibration is rebuilt separately before any fresh launch.

Revision 5 also precedes every generation-1 fresh run. A cold long-stage solver
received SIGXCPU although its protected final accounting reported 39.341316 CPU
seconds against a 40-second eligibility limit. That premature guard event is
preserved and excluded from hardness evidence. Kernel CPU limits now provide a
two/three-second soft/hard safety margin; the evaluator still rejects every
submission whose protected CPU measurement exceeds the original 6/40-second
budget. Wall limits, score, physical cases and baseline source are unchanged.
An added regression deliberately exits normally after exceeding its CPU budget
and must be rejected despite the kernel margin. The CPU-exhaustion fixture also
requires authenticated accounting and a CPU, rather than wall, termination.
`freeze_manifest_v5.json` records all fifteen checks and the preserved event.
