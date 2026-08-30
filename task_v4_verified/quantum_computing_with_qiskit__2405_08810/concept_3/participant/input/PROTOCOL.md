# One episode over stdin/stdout

Run `python3 -u solution.py`. The evaluator never imports submission code. Every message is one UTF-8 JSON object followed by `\n`. Flush each output line. Standard output is protocol-only; diagnostics may go to standard error. Do not emit NaN, Infinity, duplicate object keys, unknown fields, or booleans in numeric fields.

First, read the evaluator's object with keys `type`, `protocol`, `budget`, `parameter_order`, `bounds`, `normalization`. `type` is `start`; the other values equal the corresponding public `config.json` entries. No secret seed or family appears. A new process receives a fresh episode, and receives no other episode afterward.

Request one experiment:

```json
{"type":"experiment","prep":["Z+","X+"],"measure":"IY","time":1.25,"shots":128}
```

- `prep`: exactly two signed Pauli eigenstates, control then target; each is one of `X+`, `X-`, `Y+`, `Y-`, `Z+`, `Z-`.
- `measure`: exactly two characters in `IXYZ`, excluding `II`.
- `time`: finite real in `[0,12]`, including zero, with no discretization.
- `shots`: integer in `[1,4096]`.
- No extra keys. Read the response before requesting the next experiment.

The evaluator replies:

```json
{"type":"result","query":0,"plus":71,"shots":128,"remaining_shots":24448,"remaining_queries":191}
```

`plus` is the number of reported +1 outcomes. The other count is `shots-plus`. Query indices start at zero. Each experiment consumes one query and its requested shots, including repeats and time-zero experiments. The cumulative limits are 192 queries and 24,576 shots; an over-budget request invalidates the episode. You may finish with unused budget. A further experiment after the last allowed query is invalid.

Finish with:

```json
{"type":"estimate","omega":[1.0,0.4,-0.2,0.1,0.3]}
```

`omega` contains exactly five finite, in-bounds signed coefficients in IX, ZX, IZ, ZZ, ZI order. An optional `nuisance` key may contain four finite in-bounds nuisance values in the published order; these are not scored. There is no final acknowledgment. Exit successfully without further stdout. EOF before an estimate, malformed messages, nonzero exit, excessive output, or any resource overrun invalidates the episode. The **20-second solver wall timer starts at a trusted wrapper marker immediately before your script runs**, and includes your imports, interaction, and fitting. Variable bwrap creation is excluded, with a separate 90-second infrastructure startup deadline. The wrapper marker is consumed privately by the evaluator; your script must not emit it or expect it on stdin. The CPU limit is 18 seconds with a 19-second hard kill; one CPU is used when OS affinity is available. Address space is limited to 1 GiB per process.

The sandbox exposes only `/task` (this participant directory, read-only), `/submission` (your submission directory, read-only), system Python/NumPy/SciPy and runtime libraries, and writable `/tmp`. It has no network and no evaluator/hidden directory. The working directory is `/submission`. Add `/task/input` to `sys.path` to import the public model; do not rely on host absolute paths. Files written under `/tmp` do not persist between episodes.

Maximum stdout is 262,144 bytes, stderr 65,536 bytes, and a protocol line 16,384 bytes. The controller may not outlive its episode. Resource or parser violations fail closed and do not reveal further observations.
