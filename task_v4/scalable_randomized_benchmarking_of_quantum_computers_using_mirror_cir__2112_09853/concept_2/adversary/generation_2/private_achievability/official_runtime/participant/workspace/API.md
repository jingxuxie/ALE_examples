# JSON-lines protocol v2

One UTF-8 JSON object per newline; flush stdout after each message. Maximum
incoming line: 32,768 bytes. No blank lines, Markdown, duplicate keys, NaN,
Infinity, extra fields, boolean-as-integer values, or output after `final`.
Only one request may be outstanding. The evaluator never imports your policy.
A fresh process starts with a read-only submission tree as `/submission` and
writable scratch space `/tmp`. It receives no episode seed or hidden parameters.
All requests and responses are JSON, not Python repr. Edge IDs are zero-based
indices in the supplied `edges` list; vertices are row-major grid indices.

## Greeting: evaluator → policy

`hello` contains `type`, `version` (`mrb-active-v2`), `qubits`, `shape`, `family`,
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
{"type":"observation","matching":[0,5],"depth":24,"shots":512,"successes":260,"failures":252,"experiment":1,"context":0.021333333333333333,"shots_used":512,"shots_remaining":11488}
```

`successes` is the number of exact ideal target-bitstring outcomes, not a
Gaussian estimate or effective-polarization sample. Failures aggregate all
other strings. `context` is the midpoint of this batch in cumulative shot-budget
fraction. Experiments are independent conditional on parameters and context.
No true probability, error, or SPAM amplitude is returned.

## Irreversible target reveal

Send exactly `{"type":"ready"}`. Remaining shots may be abandoned. Response:

```json
{"type":"targets","matchings":[[0,3,5,10,13,17,21]],"quantity":"layer_entanglement_infidelity","shots_used":10000}
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

## Development and submission

The final artifact is **`OUTPUT/submission/policy.py`** plus self-contained
dependencies inside `OUTPUT/submission/`. Other research files may live
elsewhere under `OUTPUT` and are not submitted. Main evaluates
`--submission attempts/v_1/submission --policy policy.py`, not the whole attempt
directory. The supplied standalone baseline is exactly `baseline/policy.py`.

`python -B workspace/develop.py --submission . --policy baseline/policy.py
--family all --shape all --seed 2026` runs public episodes. Shape choices are
`4x4`, `4x5`, `5x5`, `all`. Family choices are the four names or `all`. A public
episode's seed is `seed + 1009*family_index + 53*shape_index`, with indices in
the orders given in `input/limits.json`. Public runs expose their seeds; official
ones do not. Development defaults to an unaudited local subprocess;
`--isolation bwrap` exercises filesystem isolation. Its report is never an
official pass. Public model instances expose `log_rate`, `error_rate`,
`contrast`, `targets`, and coefficients for debugging, not in official pipes.

Submission directories must contain at most 256 regular non-hardlinked files
totaling at most 16 MiB. Symlinks and special files are rejected. `__pycache__`
and `.git` directories are excluded. Dependencies must already be installed.
Your policy is a relative `.py` path within that directory; helper modules and
data may be included. No persistent state is carried between episodes.
