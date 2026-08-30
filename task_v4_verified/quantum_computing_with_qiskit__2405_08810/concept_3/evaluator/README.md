# Privileged evaluation

From `concept_3`:

```sh
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python3 evaluator/selftest.py
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python3 evaluator/evaluate.py participant/baseline --output adversary/baseline_hidden.json
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python3 evaluator/evaluate.py /absolute/submission/directory --output /tmp/score.json
```

`--smoke 4` runs only a prefix and cannot pass. Full scoring runs 32 episodes, one fresh process each, with at most 640 solver wall seconds plus sandbox startup and parent overhead. Startup has its own 90-second per-process deadline; unusually slow infrastructure can exceed the usual total run time and must not be treated as calibration hardness. Output includes core mean NRMSE, worst-family score, normalized `resource_score`, validity, pass/fail, reason, family breakdown, and separate solver/startup times. Resource score is the fraction of valid, within-limit episodes; it does not trade against accuracy. Exit code zero means protocol-valid, not necessarily target-passing; inspect `passed`.

The default command factory is loaded from `../authoring/sandbox.py` and invoked as `sandbox_command(participant_path, submission_path, entrypoint='solution.py', args=(), ready_marker=True)`. `run_episode(..., startup_handshake=True)` consumes the wrapper's marker before starting the 20-second solver clock. The evaluator **never imports a submission**. There is no unsafe subprocess fallback. Python callers may inject a trusted factory for infrastructure testing and explicitly select `startup_handshake`; injected factories default to plain-script timing. This is not a participant-controlled CLI option. The helper supplies separate mount/PID/network namespaces and read-only `/task` and `/submission`. `runtime.py` additionally limits address space, CPU, wall time, file size, file descriptors, line sizes, and total stdout/stderr, drains pipes nonblockingly, and kills the process group on every terminal path.

The original frozen suite has 32 episodes, eight per public family, with independent parameter/sampling child streams and a shuffled order. `generate_suite.py` uses a private 128-bit seed by default and refuses to overwrite an existing suite. Neither the seed nor the family is sent to the strategy. Suite SHA-256 and target/config commitments catch accidental mutation. Keep this evaluator, `hidden`, and `adversary` outside participant access. The public model defines the complete sampling family; no secret formula differs from it.

`selftest.py` checks dense `scipy.linalg.expm` against independently assembled matrices, zero-frequency limits, phase-sign anchors, all 32 nuisance-inclusive Jacobian ranks, strict JSON, overspending, output caps, hanging subprocesses, exit errors, and a real sandbox import/visibility probe. `design_audit.py` is a privileged local Fisher diagnostic using the true parameters, **not a legal strategy** or a passing witness.

Status is `ready_for_fresh_agent`; the empirical hardness decision is reserved for the main session after its tournament. No passing controller is known, and target achievability remains open. The builder does not run fresh agents. The baseline is a calibration reference, not a certified champion.

The `cpu_seconds` diagnostics use parent-observed child rusage, which can omit descendants in a PID namespace; they are not a solver CPU-time estimate. The CPU cap is enforced by inherited `RLIMIT_CPU`. Use measured solver wall time for runtime comparisons.
