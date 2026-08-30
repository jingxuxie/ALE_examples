# EEC hardness discovery

Final outcomes are in `FINAL_REPORT.md` and `status.json`. The primary retained
task is `concept_3` (`hard_verified_achievable`); `concept_2` is retained as a
`hard_open_candidate`. `concept_1` is solved and is not retained as hard.

`python authoring/audit_tournament.py` verifies all ten isolated attempts;
`python authoring/finalize.py` rebuilds the final score ledger and decisions.

Only an individual `concept_N/participant/` directory is distributed to a
participant. Everything else is generation-side material, including source
calculations, planted witnesses, evaluator labels, previous attempts and logs.

The three built verification modes are A (compact response improvement), B
(integration falsification), and C (inverse energy-flow construction).
`authoring/concepts.md` records the larger concept search and rejected ideas.

Each evaluator has the interface:

```sh
python concept_N/evaluator/evaluate.py /absolute/submission/directory --report /absolute/report.json
```

Evaluators read bounded JSON artifacts; they do not import or execute submitted
Python. Public workspaces define the artifact grammar and provide runnable
baselines. Python 3, NumPy, SciPy and mpmath are the generation/validation
dependencies. Grading does not need a network connection or the native paper
source. Exact dependencies for an individual method are in its participant
assets.

Fresh runs use the user-supplied allowlist runner:

```sh
python authoring/tournament.py concept_N --generation 1 --attempt 1
```

The wrapper enforces an outer 3600-second limit, requests `ultima-alpha`, starts
an ephemeral session, disables web search and mounts participant assets read-only
with an initially empty writable attempt directory. Logs and run manifests are
outside that writable directory. Two independent first-tournament attempts are
used for the static witness/design concepts. A run is not counted as a capability
failure if it never executes a meaningful agent attempt.

`authoring/grade_attempt.py` verifies the final artifact hash against the runner
manifest, snapshots the artifact outside the writable attempt directory, and
grades the snapshot. Final decisions and scores are recorded in `status.json`,
the concept-specific status files, and `FINAL_REPORT.md`.

Current participant packages are generation two. Generation-one tasks and
graders are preserved with their champions; historical source builders are not
intended to overwrite the installed generation. Generation-two compression
also preserves the pre-repair decoder: an independent one-ULP-bin counterexample
was fixed after the agent exited, and its frozen passing score was unchanged.

For a timeout, `authoring/capture_deadlines.py` preserves the last coherent
artifact observed no later than 3600 seconds. Grading uses that snapshot rather
than permitting changes during process-termination grace time. No grading
feedback is sent to agents that are still running.
