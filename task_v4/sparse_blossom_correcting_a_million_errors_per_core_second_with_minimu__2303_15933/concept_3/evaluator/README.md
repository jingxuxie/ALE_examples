# Privileged evaluator

Do not allowlist this directory, its parent, or hidden artifacts to a fresh
participant. Only `participant/` and the exact fresh attempt directory are public.

## Run a submitted program

From the concept root:

```text
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 evaluator/evaluate.py --submission "$PWD/attempts/v_1" --output "$PWD/attempts/v_1_report.json" -- /usr/bin/python3 /submission/solution.py
```

Create `attempts/v_1` before launch. Its parent `attempts/` is NOT mounted.
Reports and transcripts must be outside the mounted submission leaf. Default
evaluation uses all 12 frozen private episodes. `--suite training` and `--limit`
are diagnostics only. No worker code is imported by the evaluator: it imports
only the private trusted sampler. Public helper imports occur only inside workers
or in separate privileged science-validation scripts, never in the scorer.

The evaluator checks the episode/target SHA-256 manifest before launching a worker.
`build_data.py` refuses to overwrite existing episodes. `revise_design.py` records
the one-time pre-fresh v1-to-v2 generation migration and refuses a second migration
through the action-count guard. Do not run it on the final package.

## Isolation

Bubblewrap is mandatory. It binds only system `/usr`, `/lib`, `/lib64`, `/bin`,
`/etc` read-only; new private `/proc`, `/dev`, ephemeral `/tmp`; the read-only
participant package; the exact writable submission directory; and one read-only
trusted supervisor source file containing no rates/seeds. All other paths are
absent. Network, PID, IPC, user, UTS, and supported cgroup namespaces are unshared.
Capabilities are dropped and the environment is replaced with a short allowlist.

The parent owns hidden rates, sampling RNG state, and scores. No rates or seeds
enter worker argv, environment, files, or JSON messages. `/proc` cannot show the
outside evaluator. A nested sandbox may reject bubblewrap's network unshare;
run this privileged evaluator outside that parent sandbox with explicit approval.
NEVER disable the evaluator's isolation to work around this. The public local
driver deliberately uses plain subprocesses with disclosed training rates only.

## CPU accounting

Do not interpret the host bubblewrap monitor's `wait4` usage as worker CPU.
The trusted in-namespace supervisor waits on the actual Python worker, aggregates
wait4 CPU including descendants, applies RLIMIT_CPU/AS/CORE/FSIZE/NOFILE, and
authenticates its meter with a per-episode HMAC key. That key arrives over the
supervisor's stdin control line, is consumed before the worker starts, and is
never in argv/environment. The supervisor disables dumpability before fork/exec,
preventing child access to its memory and `/proc` descriptors. The child's exec
replaces inherited memory. Descendants left at worker exit are killed/reaped.
A forged meter, nonzero exit, or missing meter invalidates the episode.

CPU is a 60-second per-episode validity cap. The wall watchdog is 900 seconds
after supervisor readiness plus a 300-second initialization allowance. Pipe
reads AND writes have deadlines, including the potentially large initial spec.
Tests include a known two-second process-time burn and a hard CPU-limit kill.
The fresh coding allowance is one hour, separate from these evaluation limits.

## Scientific audits

`adversary/validate_science.py`: independent XOR-convolution PMFs, event-sampler
moments, independent multinomial sampling, analytic gradients, reference versus
full intervention Jacobian ranks, and log-rate Fisher bounds for uniform,
action-11-heavy, and true-rate diagnostic designs.

`adversary/validate_inverse.py`: noiseless recovery from four truth-independent
initializations per private episode. This is an empirical global ambiguity check,
not a theorem. `adversary/validate_protocol.py`: sandbox visibility, CPU, malformed
rates/queries, oversize shot requests, and forged meter tests.

The true-rate Fisher portfolio is validation ONLY. The actual passing reference
program chooses a fixed design from public bounds and fits only observed syndrome
histograms; it is latent-blind and obeys the same API, budget, and sandbox.
