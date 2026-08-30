# Infrastructure diagnosis and validated no-model recovery preflight

Date: August 28, 2026.

## Bottom line

The current host's `/tmp` mountpoint blocks bubblewrap setup. A clean
`CODEX_HOME`, the correct native executable, and a private `TMPDIR` do not fix
that mount operation. A new private root with a fresh `/tmp` inode DOES work:
the installed Codex sandbox completed all six synthetic confinement checks
under the original runner's filesystem profile. No model session was launched.

The existing concept_2/v_1 is infrastructure-blocked, not a solver failure.
It was neither signaled nor modified by this investigation.

## Exact evidence

- `bwrap.trace:195`: changing mount propagation succeeds.
- `bwrap.trace:196`: `mount("tmpfs", "/tmp", "tmpfs", MS_NOSUID|MS_NODEV, NULL)`
  never returns during the bounded probe. Its process is in `D` state at
  `rwsem_down_write_slowpath`, syscall 165.
- `private_tmpfs.json`: mounting tmpfs at an empty private diagnostic path
  inside a new user/mount namespace succeeds, exit 0, 0.567 seconds.
- `unshare_user.json` and `unshare_mount.json`: user and mount namespace
  creation both succeed. This is not a blanket user-namespace prohibition.
- `strace.json`: credential-free, private-TMPDIR `strace /bin/echo` succeeds,
  exit 0, 0.699 seconds, with a nonempty trace. Ptrace is not universally broken.
- `attempt_v1_state.json:6`: actual PID 665600 waits in `futex_wait_queue_me`;
  fd 0 is `/dev/null`, not a pending interactive input stream.
- `attempt_v1_state.json:23`: its child 666376 is `codex-linux-san`, in `D`
  state at `rwsem_down_write_slowpath`. Its executable is the expected
  clean-home native Codex hardlink. Its syscall/stack are permission-denied,
  so the exact syscall of THAT process was not established. The independently
  reproduced bubblewrap mount failure identifies the infrastructure problem.
- `sandbox_help_correct.json`: `codex sandbox --help` succeeds, exit 0.
  In this 0.150.1 CLI, `linux` is not a sandbox subcommand: `codex sandbox
  linux --help` attempts a sandboxed command instead of printing the CLI help.
- `legacy_allowlist_echo.stderr`: enabling `use_legacy_landlock` with the
  same allowlist panics: `permission profiles requiring direct runtime
  enforcement are incompatible with --use-legacy-landlock`. Do not use that
  flag as an allowlist-preserving fallback.

The kernel lock owner was not identified; no unrelated process command lines
or environment contents were inspected. Do not infer a specific kernel bug
or lock-owning process from the wait-channel name alone.

## Validated route

`private_root_probe.py` is a DIAGNOSTIC, not a model launcher. It:

1. Requires fresh user, private mount, and PID namespaces.
2. Mounts a tmpfs root at an owned diagnostic directory, NOT host `/tmp`.
3. Exposes only normal system runtimes, selected configuration/device files,
   the native Codex executable, the unchanged runner, a credential-free clean
   home, synthetic read-only participant assets, and synthetic writable output.
4. Creates a fresh `/tmp` inside that root and mounts `/proc` for the new PID
   namespace. It does not bind the host task tree, home, or authoring directory.
5. Uses `pivot_root`, detaches the old root, and removes its mountpoint BEFORE
   executing Codex. Plain `chroot` was insufficient: nested bubblewrap then
   failed to create a user namespace.
6. Executes `codex sandbox -P benchmark` with the same filesystem entries as
   `run_allowlisted_codex.sh`, approvals never, web search disabled, and model
   explicitly `ultima-alpha`. It does not enable legacy Landlock or bypass
   sandboxing. The sandbox diagnostic subcommand does not accept strict-config;
   the actual runner remains unchanged and still uses strict-config.

`private_root.json`: exit 0, 29.279 seconds, no stderr.
`private_root.stdout:34`:

```json
{"participant_read": true, "output_write": true, "participant_write_denied": true, "excluded_read_denied": true, "runtime_config_read_denied": true, "network_denied": true}
```

All negative probes use synthetic files or the credential-free diagnostic
configuration. No hidden research artifact was read or mounted into the test.
This is a bounded functional preflight, not an exhaustive security audit or
an authenticated model-session test.

## Handoff for a real rerun, only when separately authorized

Adapt the private-root bootstrap in the main launcher, not the global runner.
Mount only the specific real participant directory read-only, its NEW empty
output writable, the fresh runtime home, the original runner, and required
system runtimes. Do not mount the broader task, attempts, authoring, or home
trees. Preserve the fresh model/catalog/auth setup; use its native
`packages/bin` on PATH, and set HOME/CODEX_HOME inside the isolated root.

After `pivot_root` and detaching the old root, execute the unchanged required
`run_allowlisted_codex.sh --model ultima-alpha --effort high --task-read-only
PARTICIPANT NEW_EMPTY_OUTPUT PROMPT`. Preserve its read allowlist and disabled
escalation. The no-model preflight should pass before starting a new full
3600-second solver budget. Record v_1 as infrastructure-invalid, not as
empirical solver failure. Do not stop its process without the user's approval.

The actual model-run integration, authentication, and one-hour attempt have
NOT been tested or launched here. A healthy worker with an independent `/tmp`
is the alternative if the main launcher does not adopt this bootstrap.

## Change boundaries

All diagnostic files are under this mode-0700 directory. No credentials were
copied. No global runner, configuration, host mount, or actual attempt file
was changed. Only owned diagnostic process groups were signaled on timeout.
The runner SHA-256 still matches the actual attempt metadata:

`9625e083fce46db66609c63bca91b7177bd6165ac79e2efbfb02c8cc5aa43da3`
