# Trusted streaming evaluation

Run from the concept directory:

`python3 evaluator/evaluate.py --submission participant/baseline --output attempts/baseline_official.json`

The parent parses only trusted hidden JSON and untrusted prediction JSON;
it never imports submission code, models, or participant modules.
Only `id`, `L`, and exact `fields` enter the child process, after `READY`.
Family labels and reference targets remain in the trusted parent. No
hidden cases file exists or is mounted during startup. The copied
`sandbox.py` is the shared Bubblewrap/prlimit streaming isolation helper.

Official resources are 60 seconds startup, 3 seconds inference after
input delivery, four-core CPU affinity and 2,048 MiB address space.
The submission must reply with one JSON line and exit.

Bubblewrap needs evaluator-side escalation when launched inside a nested
agent sandbox. There is no unsandboxed fallback; isolation errors fail
closed. `authoring/benchmark_official.py` checks the exact protocol using
public validation data without consulting hidden labels. The local
`benchmark_stream.py` is diagnostic, not an official sandbox pass.

`targets.json` must be frozen before a fresh solving attempt. Data hashes
and private stratum checks live in `hidden/manifest.json`. Do not mount
the concept root or `hidden/` into a participant environment. Mount only
`participant/` and the selected submission directory. Never choose a
submission directory containing trusted or private files.

Every result contains `core_score` (overall RMSE, lower is better),
`worst_family_score` (worst-family RMSE, lower is better), `valid`,
`evaluator_valid`, `resource_score`, `runtime_seconds`, `passed`, and
`reason`. A valid isolated run has resource score 1. Accuracy failure is
still a valid evaluation. Submission failures have `valid=false` and
`evaluator_valid=true`; infrastructure failures have both false and null
scores where unavailable. `reason` and `error_category` distinguish them.
Bubblewrap startup stderr is preserved for infrastructure diagnosis.
Final packaging/alias changes are left for main's validation, as requested.
