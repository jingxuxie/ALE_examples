# Fresh execution isolation audit — August 28, 2026

## Status

VALIDATED infrastructure route, not a scientific result. The unchanged provided runner executed an isolated `ultima-alpha` synthetic probe and returned `PROBE_PASS` in 67.249 seconds. Zero concept attempts were launched by this support task. Additional submission, exact-profile, `/proc/PID/root`, input-validation, and watchdog probes passed.

Use approved escalated execution to start these helpers. Do not launch them through the parent session's hanging default sandbox. Escalation starts an externally isolated controller, not an unrestricted participant.

## Exact launch APIs

```bash
AUTHORING=/home/xuandong/mnt/jingxu/ALE/tasks_v4/qulacs_a_fast_and_versatile_quantum_circuit_simulator_for_research_pur__2011_13524/authoring
python3 -B "$AUTHORING/launch_fresh.py" preflight
python3 -B "$AUTHORING/launch_fresh.py" preflight --agent-smoke
```

The first command is model-free. The second adds one infrastructure-only model probe, bounded to 240 seconds. Both use synthetic participant directories and initially empty outputs under `authoring/isolation_*`, not concept attempts.

Only when a concept package has separately been validated and an attempt authorized:

```bash
python3 -B "$AUTHORING/launch_fresh.py" run \
  --participant "$PARTICIPANT" --output "$EMPTY_OUTPUT" \
  --prompt-file "$PROMPT_FILE" --confirm-concept-attempt
```

Use absolute paths. Participant must be an existing directory named `participant`; output must exist and be empty. Symlinks, hardlinks, special files, overlapping roots, and `.git`/`.codex`/`.agents` in participant trees are rejected. `run` first repeats model-free isolation gates, then invokes `/home/xuandong/mnt/jingxu/ALE/run_allowlisted_codex.sh --model ultima-alpha --task-read-only ...`. The actual runner has a 3600-second deadline; preflight/setup time is additional. Failed gates start no concept attempt. This helper does not validate scientific package correctness.

Evaluator submission subprocess API:

```bash
python3 -B "$AUTHORING/isolation.py" \
  --submission "$SUBMISSION" --work "$EMPTY_WORK" --seconds 60 \
  -- /usr/bin/python3 "$SUBMISSION/solve.py"
```

Submission is read-only; only the initially empty work directory is writable, plus private tmpfs scratch. No evaluator, hidden directory, sibling output, parent home, or parent process filesystem is mounted. Optionally add `--stdin` to forward at most 1 MiB of explicitly supplied public per-case input as bytes, never a hidden-file descriptor. Default stdin is `/dev/null`. Keep `isolation.py` and `isolation_bwrap.py` together if reusing them elsewhere. Invoke the CLI as a separate evaluator subprocess; the internal watchdog is not an in-process concurrent evaluator API.

## Thread-budget limitation

The helper does **not** strictly enforce advertised thread budgets. It sets `OPENBLAS_NUM_THREADS=1`, `OMP_NUM_THREADS=1`, and `MKL_NUM_THREADS=1`, plus `RAYON_NUM_THREADS=2` and `TOKIO_WORKER_THREADS=2`. These are environment hints that submitted code can override or ignore. There is no CPU-affinity restriction, protected cpuset, maximum thread count, or aggregate CPU-time/memory accounting. Therefore this helper alone does not establish compliance with A=4 threads, C=1 thread, or E=1 thread. Isolation validity must not be presented as resource-budget or scientific-performance validity. No affinity option was added during the active fresh run; enforce and validate resource budgets separately before accepting evaluator timing results. Unprotected `taskset` or environment settings alone should not be described as strict limits against an untrusted submission.

## Provenance and active-run handoff

Read-only design references included the existing `spectral_and_thermodynamic_properties_of_the_sachdev_ye_kitaev_model__1610_03816/authoring/isolation_runtime.py`, `bootstrapping_the_o_n_archipelago__1504_07997/authoring/private_root_launch.py`, and `variational_study_of_u_1_and_su_2_lattice_gauge_theories_with_gaussian__1805_05190/authoring/isolation_adapter.py` under `tasks_v4`. These wrappers were not imported into or exposed to the fresh participant. The final helper hashes and native runtime hashes are recorded in `isolation_audit.json` and the individual `runtime-audit.json` files.

Diagnostics, task-local edits, synthetic probes and the network-namespace equivalence adapter were executed using explicit `require_escalated` requests with justifications. That approval was not used to run participant code unrestricted: outer filesystem/PID isolation and the native inner filesystem restrictions remained in force, with inherited network-denial filters added. Every model probe was gated on successful synthetic isolation checks.

The user subsequently reported a separately launched A attempt at `isolation_fresh_4iyggdyc`. This support task did not launch, stop, modify, or evaluate that attempt. Cleanup targeted only completed synthetic runtimes with `scientific_attempt=false`; that active fresh root was excluded. The zero-attempt statement describes this support task, not all work performed concurrently by the main agent.

## Boundary and explicit adaptation

- The global runner is unchanged: SHA-256 `9625e083fce46db66609c63bca91b7177bd6165ac79e2efbfb02c8cc5aa43da3`.
- Outer bubblewrap exposes read-only system runtime, the runner file, read-only participant, writable output, and one fresh runtime home. It provides private mount, user, PID, IPC and UTS namespaces, private `/tmp` and `/dev`, and drops capabilities. Only the controller retains API networking.
- The runner still applies its original narrow filesystem profile, `approval_policy=never`, disabled web search and `--ephemeral`. No full-access mode, alternate permissions profile, or disabled filesystem sandbox is used.
- Explicitly approved `isolation_bwrap.py` is pinned as `bwrap` in the fresh PATH because this installed native sandbox resolves PATH before the packaged resource. It retains all filesystem arguments and existing seccomp filters, removes only `--unshare-net`, and adds an inherited seccomp filter denying socket creation/communication, io_uring, process-memory/descriptor acquisition and mount/namespace escape operations. Existing `--seccomp` filters are retained using stackable `--add-seccomp-fd`. Adapter activation is printed in each payload log. This is not a Landlock-only or seccomp-only filesystem sandbox.
- Networking is stricter than the original profile: AF_INET, AF_INET6, AF_UNIX and AF_NETLINK sockets are denied. Software requiring Unix sockets, io_uring or its own namespaces may fail; classify such failures as infrastructure incompatibility, not scientific hardness.
- Each runtime copies only three native ELF executables, allowlisted authentication fields, a sanitized single-model catalog, and the reasoning-effort scalar. No parent logs, sessions, instructions, memories, plugins, skills or environment are copied. Fresh config disables these integrations. Generated CODEX_HOME is removed after completion/failure; audit hashes, synthetic outputs and fresh logs remain outside participant visibility.
- Missing isolation support fails closed. No fallback broadens filesystem or network access. Landlock ABI 1 is available but cannot alone preserve truncation restrictions; it is deliberately not used as an equivalent fallback.

## Audit evidence

Paths here are relative to this authoring directory. Machine-readable summary is `isolation_audit.json`.

| Evidence | Result |
| --- | --- |
| `isolation_agent_smoke_dmf60yqe/agent.log`, `invocation.json`, `result.json`, `output/probe-result.json` | Actual unchanged-runner `ultima-alpha` smoke: 67.249 s, exit 0, PROBE_PASS; empty initial output; no scientific attempt |
| `isolation_runner_preflight_slnsv9d3/` | Exact benchmark filesystem profile with adapter: 44.352 s, all checks pass |
| `isolation_submission_preflight_s5gs8r90/` | Submission boundary with adapter: 9.903 s, all checks pass |
| `isolation_runner_preflight_ba4t30us/`, `isolation_submission_preflight_ivmu82zd/` | Additional `/proc/PID/root` escape probes pass, 72.257 s and 24.231 s |
| `isolation_validation_r5njl4y6/result.json` | Overlap, nonempty output and symlink rejection; syntax; timeout/reaping at 1.005 s |
| `isolation_runner_preflight_evigh3h_/result.json` | Unadapted exact profile timed out at 90 s; a newly created bwrap was observed in D state at `rtnetlink_rcv_msg` |

Private-paper and credential probes test openability only; they never read their contents. Synthetic canaries test actual read/write/truncate rejection. Successful checks also cover symlink escape, host loopback, capabilities, no-new-privileges, seccomp activation and parent-session exclusion.

## Limitations and failure classification

Direct user/mount namespace creation succeeded; minimal bubblewrap succeeded in 4.25 s and full-device bubblewrap in 11.21 s. Thus a five-second timeout was not evidence that user namespaces were unavailable. The exact profile nevertheless showed intermittent kernel networking stalls. The adapter is a task-local execution workaround, not a host-kernel repair. No sysctl, host configuration, runner or unrelated process was changed.

The initial probe also encountered two CLI-version errors: this build rejects `--strict-config` for `codex sandbox` and uses `codex sandbox --permission-profile benchmark -- COMMAND`, not `codex sandbox linux`. Probe syntax was corrected; the provided runner retains `--strict-config` for `exec`.

The watchdog sends SIGKILL at the deadline and cleans only descendants of its dedicated helper process. Kernel-uninterruptible tasks can outlast the deadline until their syscall returns; the failed native probe's two remaining PIDs later disappeared. Successful final probes leave no owned descendants. The main session's default sandbox itself is not repaired. Infrastructure timeout, sandbox/configuration failure or API failure is not evidence of scientific hardness.
