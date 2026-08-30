# JSON-lines protocol v3

One UTF-8 JSON object per newline; flush stdout after each message. Each policy
stdout JSON line is limited to 32,768 bytes before its newline. No blank lines, Markdown, duplicate keys, NaN,
Infinity, extra fields, boolean-as-integer values, or output after `final`.
Only one request may be outstanding. The evaluator never imports your policy.
A fresh process starts with a read-only submission tree as `/submission` and
writable scratch space `/tmp`. It receives no episode seed or hidden parameters.
All requests and responses are JSON, not Python repr. Edge IDs are zero-based
indices in the supplied `edges` list; vertices are row-major grid indices.

## Greeting: evaluator → policy

`hello` contains `type`, `version` (`mrb-active-v3`), `qubits`, `shape`, `family`,
`edges`, `limits`, `max_matching_size`, `target_matching_size`, `target_reveal`
(`after_ready`), and `families`. The actual `family` is one of `local_clusters`,
`distant_pairs`, `anticorrelated`, `spam_drift`; there is no hidden family-label
guessing requirement. `limits` gives `shots_budget`, `max_experiments`,
`min_shots`, `max_shots`, `max_depth`, `target_count`.

## Acquisition: policy → evaluator

```json
{"type":"experiment","matching":[0,5],"depth":24,"shots":512}
```

Exactly these four keys are required. A matching is a sorted list of distinct
integer edge IDs whose endpoint sets are disjoint. Its size cannot exceed
`max_matching_size`. `[]` is legal. Depth is an integer in `[0,256]`, divisible
by two. Shots is an integer in `[32,4096]`. Every shot, including depth zero,
costs one budget unit; depth does not change its price. No request can overspend
the remaining budget or exceed 768 total requests. Budgets reset each episode.

The response has exactly the following fields (numbers shown are illustrative):

```json
{"type":"observation","matching":[0,5],"depth":24,"shots":512,"successes":260,"failures":252,"experiment":1,"context":0.128,"shots_used":512,"shots_remaining":1488}
```

`successes` is the number of exact ideal target-bitstring outcomes, not a
Gaussian estimate or effective-polarization sample. Failures aggregate all
other strings. `context` is the midpoint of this batch in cumulative shot-budget
fraction. Experiments are independent conditional on parameters and context.
No true probability, error, or SPAM amplitude is returned.

## Irreversible target reveal

Send exactly `{"type":"ready"}`. Remaining shots may be abandoned. Response:

```json
{"type":"targets","matchings":[[0,3,5,10,13,17,21]],"quantity":"layer_entanglement_infidelity","shots_used":1600}
```

The example shows one matching for readability; the actual list contains 96.
Targets were generated before your first request, independently of shot noise
and private error parameters. Their size is `target_matching_size`, so none
was legally queryable. They are not fresh noisy measurements. After reveal,
only the final message is allowed; `ready` cannot be repeated.

## Predictions and termination

```json
{"type":"final","predictions":[0.053,0.071]}
```

Provide exactly one finite real number in `[0,1-4**(-qubits)]` for each target,
in the supplied order (96 numbers, not the two shown). The response is exactly
`{"type":"done"}`. Exit with status zero before the episode's 90-second wall
deadline, without additional stdout. Teardown shares that same deadline;
there is no shorter post-final timeout. Predictions are errors of **one complete layer**, not log decay rates,
success probabilities, average gate infidelities, or depth-multiplied errors.

Malformed messages, resource violations, EOF before final, or nonzero exit
invalidate the episode; there are no retries or free error-feedback probes.
The evaluator may close pipes immediately on error; a policy must not require
an error response. Each family score is zero if any of its episodes is invalid.

## Runtime resources

Each episode allows 90 seconds wall time, including startup and teardown, and
60 seconds aggregate kernel-accounted CPU time, with a 0.25-second accounting
tolerance. Official evaluation counts user and system CPU across the isolated
process tree, including threads, exited workers, and auto-reaped descendants,
using a parent-controlled cgroup v2 `cpu.stat` counter. The policy cannot access
the counter descriptors, host cgroup filesystem, or user-service bus. The parent
cleans up only its own episode group, waits until it is empty, then reads the
final counter. Existing per-process `RLIMIT_CPU` soft/hard limits remain 60/61
seconds; they do not replace the aggregate limit.

Each process has a 1536 MiB address-space limit (`RLIMIT_AS`) and a
64-file-descriptor limit (`RLIMIT_NOFILE`), including its standard streams.
Memory is limited per process, not as an aggregate process-group allocation.
Reported launcher peak RSS is diagnostic, not aggregate memory accounting.

Official `bwrap` evaluation requires writable cgroup v2 accounting and fails
closed without it. The trusted evaluator CLI automatically re-executes once
in a transient user-owned systemd service when its current cgroup is not
writable. This requires the host's user-service bus and `systemd-run`; no
downloads or policy-side service privileges are needed. No CPU quota, memory
group limit, or new policy process-count restriction is introduced.

Every writable regular file has a maximum size of **256 KiB (262,144 bytes)**
under `RLIMIT_FSIZE`. This applies to scratch files in `/tmp`, not only to
stderr. Stderr output separately has a 256 KiB cap. Policy stdout must follow
the JSON-lines protocol, with at most 32,768 bytes per line before its newline.
The file-size and descriptor limits are existing enforcement, not additional
shot costs or changes to the experimental model.

## Development and submission

The final artifact is **`OUTPUT/submission/policy.py`** plus self-contained
dependencies inside `OUTPUT/submission/`. Other research files may live
elsewhere under `OUTPUT` and are not submitted. Main evaluates
`--submission attempts/v_3/submission --policy policy.py`, not the whole attempt
directory. The supplied standalone baseline is exactly `baseline/policy.py`.

`python -B workspace/develop.py --submission . --policy baseline/policy.py
--family all --shape all --seed 2026` runs public episodes. Shape choices are
`4x4`, `4x5`, `5x5`, `all`. Family choices are the four names or `all`. A public
episode's seed is `seed + 1009*family_index + 53*shape_index`, with indices in
the orders given in `input/limits.json`. Public runs expose their seeds; official
ones do not. Development defaults to an unaudited local subprocess that remains
usable without a cgroup filesystem or user-service bus. Audit mode labels
`RUSAGE_CHILDREN` CPU diagnostics as inexact because descendant usage can be
missed, and cannot certify even a perfect prediction score. `--isolation bwrap`
exercises filesystem isolation and strict kernel CPU accounting when launched
from a suitable trusted host user service. A development report is never an
official pass. Public model instances expose `log_rate`, `error_rate`,
`contrast`, `targets`, and coefficients for debugging, not in official pipes.

Submission directories must contain at most 256 regular non-hardlinked files
totaling at most 16 MiB. Symlinks and special files are rejected. `__pycache__`
and `.git` directories are excluded. Dependencies must already be installed.
Your policy is a relative `.py` path within that directory; helper modules and
data may be included. No persistent state is carried between episodes.
