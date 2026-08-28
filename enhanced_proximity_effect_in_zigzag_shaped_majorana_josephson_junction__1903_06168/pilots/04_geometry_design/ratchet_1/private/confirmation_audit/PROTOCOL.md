# Independent confirmation audit

Write scope: this directory only. No public, attempt, reference, pool, evaluator,
or author-tool changes. No nested agents, solver launches, numerical grading,
duplicate forward computation, additional cases, or automatic ratchets.

The watcher reads only `../runs/confirmation/launch.json` and `score.json`.
It does not access the attempt, transcript, or intermediate solver outputs.
Attempt/transcript inspection is forbidden before `launch.json` exists; the
audit additionally waits for terminal launch and scoring reports before inspecting
the completed implementation. A malformed, missing, failed, or incomplete grade
is unknown, never an invented score of zero.

From this directory:

```sh
python -B wait_for_completion.py --wait-seconds 7200 --poll-seconds 30
```

Once the trusted reports are ready, the independent audit will record:

- Exact core score, worst-family score, feasibility, and per-case outcomes.
- Launch, solver, and grader execution statuses and reported resource usage.
- Whether the submitted implementation is complete and its actual algorithm.
- Source-backed evidence for unresolved technical components, distinguished
  from clerical/schema/dependency/resource-handling-only failures.
- Any broadly reusable shortcut if the task is solved, without inferring a
  universal method from one result or from the frozen source reference.
- Consistency between participant claims, delivered code, and trusted scores.
- A cautious solved/moderate/hard screening interpretation; the fixed source
  anchor is 1, all three operating points are exposed, and main owns acceptance.

No screening conclusion is preregistered as an outcome. Completing the reference
gate is not proof that a fresh implementation solved the task. Conversely, a
failed grader cannot establish technical hardness. Final evidence and artifacts
will be saved here without influencing the running confirmation.

## Independent generic control

Main separately owns `../generic_baseline/PROTOCOL.md`, `../generic_baseline/code/solve.py`,
and the queued `../runs/generic_probe/score.json`. If the control's trusted score
is ready when the confirmation audit finishes, include its fixed profile sweep,
ordinary refinement, feasibility, and exact scores in the interpretation. Do not
rerun or modify this control. It was designed without confirmation-source access,
according to main's preregistered provenance; inspect that evidence independently.

A cheap fixed sweep that robustly reaches the source references rules out calling
this task frontier-hard merely because a particular fresh confirmation performs
poorly. A pending or failed control grade is unavailable evidence, not zero. The
confirmation attempt/transcript access gate remains unchanged.
