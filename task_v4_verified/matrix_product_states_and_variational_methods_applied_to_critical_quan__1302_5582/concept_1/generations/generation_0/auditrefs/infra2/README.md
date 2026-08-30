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
