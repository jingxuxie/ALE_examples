# Private infra5 phase diagnostic

Authorized scope: this directory only for retained artifacts. This is not an official regrade, fresh attempt, physics search, or target change. Exactly the existing odd-short request `g1_ea6c7b33ae689d1cfeeec166ffd0a4a0` may be run three times maximum. The completed v3 submission and participant are checked byte-for-byte and mounted read-only.

The copied runner retains CPU6/wall30, child soft8/hard9, inherited outer soft10/hard11, the 150-second operational watchdog, memory/file limits, fail-closed bwrap, and the strict original success predicate. Its normal ephemeral `/tmp` staging is retained to avoid changing source-I/O placement, automatically removed after each run, and checked for cleanup. All retained outputs stay here.

The instrumented worker records early Python CPU, pre/post-RLIMIT CPU, CPU immediately before seccomp loading, and CPU/wall immediately before user runpy. A bounded blocking pipe sends these trusted pre-user records to the nondumpable supervisor; the child closes its writer before any user code executes. The parent remains blocking-wait4 plus SIGALRM, not polling. Its protected terminal record separately includes child wait4 user/system CPU and parent CPU before/after supervision. Extra fields remain inside the existing 4096-byte accounting limit.

Run once, with approved host/bwrap execution:

    /usr/bin/python -I -B run_diagnostic.py --execute

`runs/` is exclusively created, so a repeated command refuses to launch again. There are no automatic retries. Full raw resource, output, request, process and staging manifests are retained. No state energy is measured and no scientific score is computed.

Instrumentation perturbs startup timing and adds a passed descriptor. Phase attribution can localize an observed recurrence but cannot reconstruct an earlier uninstrumented event. If it does not recur, the result is inconclusive, not evidence that the harness is correct or that the solver is defective. No more than three diagnostic calls are authorized.
