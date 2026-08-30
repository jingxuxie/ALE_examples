# Task-local generation and evaluator isolation

All implementation and audit files live in this `authoring/` directory. The
repository runner and all concept files are unchanged by this sidecar. Audits
use plain processes, not a model session; dummy authentication is used for the
Codex sandbox audit.

## Generation: main launches, not the audit

Run from an escalated host shell while the parent command sandbox is broken.
Use canonical paths: `/home/...` is an alias for `/srv/home/...` on this host,
and mounted participant/output trees reject symlink components.

```bash
ROOT=$(realpath /home/xuandong/mnt/jingxu/ALE/tasks_v4/stim_a_fast_stabilizer_circuit_simulator__2103_02202)
python3 -B "$ROOT/authoring/launch.py" \
  --participant "$ROOT/concept_1/participant" \
  --output "$ROOT/concept_1/attempts/v_1" \
  --limit 3600
```

The output directory must already exist and be empty. Use distinct `v_N`
directories for independent attempts, including parallel `concept_2` or
`concept_3` repetitions. Reusing a previously launched attempt is refused.
The API is `launch(participant, output, *, prompt_file=None,
source_codex_home=None, limit=3600)` in `launch.py`.

Each invocation gets its own mode-0700 runtime home, private user/mount/PID/IPC
namespaces, detached old root, and bounded process-tree supervisor. Runtime
homes are cleaned up after completion. Only authentication, model catalog,
and native executables are taken from the source runtime; sessions, history,
project settings, skills, hooks, and MCP configuration are not copied. Custom
providers fail closed pending explicit review. Shell environment inheritance
and shell snapshots are disabled; runtime executable helpers remain on PATH.

The exact fixed runner invocation is:

```text
/home/xuandong/mnt/jingxu/ALE/run_allowlisted_codex.sh --model ultima-alpha --effort xhigh --task-read-only PARTICIPANT OUTPUT PROMPT
```

The unchanged runner supplies strict configuration, its original filesystem
allowlist, approval denial, disabled web search, and ephemeral execution. Its
original SHA-256 was
`9625e083fce46db66609c63bca91b7177bd6165ac79e2efbfb02c8cc5aa43da3`.
The shared runner changed externally during generation. After a byte-level
access-control audit and repeated isolation checks, later launches pin
`06f4693741de6587283d2cf78d91895e5a74c1230c9960b5457f8cc536cf0394`.
`runner_change_audit.json` and `runner_versions/` preserve the evidence:
only comments and numerical-library thread defaults changed. Two launches
blocked by the hash guard before any model call are excluded from the
scientific results. This session never edited the shared runner.
The participant is mounted read-only; the selected attempt is writable. No
evaluator, hidden input directory, previous attempt, or host home is mounted.
The controller's private runtime is not in the tested command's read allowlist
except its native packages and argument-helper directories.

Generation retains its original 3600-second wall deadline, including private
root setup but excluding preparation of the fresh runtime. Logs and metadata
are under `authoring/launch_records/`; the launcher prints the exact record
path. Logs are saved when the supervised process ends. Nonzero infrastructure
exits require inspection and are not evidence of an agent solving failure.

## Concept 1 evaluator

Put this authoring directory on the trusted evaluator's import path, then:

```python
from sandbox import run_file

answer, telemetry = run_file(
    submission, participant, input_path, timeout=45, memory_mb=2048
)
```

`submission` is a canonical directory containing `solve.py`. `participant` is
the canonical public directory. `answer` is a parsed JSON object or `None`;
the scorer, validation rules, hidden labels, and other hidden cases stay in the
parent process. The helper never imports submitted code or unpickles results.

The isolated command is:

```text
/usr/bin/python3 -B ORIGINAL_SUBMISSION/solve.py --input /input/instance.json --output /work/answer.json
```

Only a private copy of the current input file is mounted, not its source
directory. Read-only `/task` and `/submission` mounts plus the original
canonical absolute participant/submission paths preserve baseline-relative
imports. `PYTHONPATH=/task/workspace:/submission` exactly. `/work` and `/tmp`
are fresh scratch storage. Broad read-only `/usr`, selected system
configuration, the compiler, NumPy, and SciPy are available; user-site packages
and the Codex runtime are not. There is no arbitrary extra-read option.

Evaluation uses a separate network namespace, seccomp restrictions, zero
effective/permitted/bounding capabilities, no-new-privileges, and one CPU.
The address-space limit defaults to 2048 MiB. Submitted trees reject symlinks,
hard-linked regular files, and special files. Output is read without following
symlinks or blocking on FIFOs. Input is capped at 16 MiB, JSON answers at 8 MiB,
captured stdout/stderr together at 8 MiB, and individual created files at 64 MiB.

### Timing and failures

Setup has its own **60-second deadline**. A trusted pipe passes a monotonic
timestamp immediately before exec; the child closes that descriptor before
any submitted code runs. The requested **45-second solver wall clock** starts
at that timestamp, including Python startup, imports, compilation, and output
I/O. An independent CPU-time limit also applies. Generation timing is unchanged.

- `elapsed_seconds` and `execution_seconds`: solver execution, excluding setup.
- `setup_seconds` and `wall_seconds`: separate infrastructure and total timing.
- `ready_received`: trusted setup reached the exec boundary.
- `timed_out`: solver exceeded its execution deadline.
- `setup_timed_out` or nonempty `infrastructure_error`: retry/abort grading;
  **do not score this as an agent failure**.
- `returncode`, `stdout`, `stderr`, `output_limited`, and optional `answer_error`
  describe the submitted process and bounded result handling.

The supervisor kills the process group and namespace init on timeout; the
audit also checks that a descendant which calls `setsid()` does not survive.
Concepts 2 and 3 use their static artifact checkers and do not need `run_file`.

## Reproducible audits

```bash
python3 -B "$ROOT/authoring/audit_isolation.py"
python3 -B "$ROOT/authoring/audit_timing.py"
```

Reports: `isolation_audit.json` and `timing_audit.json`. The isolation audit
covers real nested Codex command execution, hidden paths and `/proc` aliases,
runtime authentication/config denial, host process denial, read-only mounts,
output writes, network denial, one CPU, memory limits, zero capabilities,
compiler/numerical imports, and the supplied public baseline. Timing tests
cover the closed ready descriptor, solver-only timeout, detached descendant
cleanup, and classification of setup failures as infrastructure.

The installed CLI syntax is `codex sandbox [OPTIONS] [COMMAND]...`, not
`codex sandbox linux`. It rejects `--strict-config` for the diagnostic sandbox
subcommand. The audit omits that diagnostic-only unsupported flag; the real
generation runner still uses `--strict-config` unchanged. Native sandbox and
patch helper symlinks are provided inside the already-allowlisted packages.
Direct mount syscalls avoid the observed shell-mount hangs; there is no bwrap
or filesystem-policy bypass and no weaker isolation fallback.
