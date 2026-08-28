# Localized statistics decoding: ALE task review bundle

This directory preserves three paper-derived task designs, their known-good
solutions, behavioral evaluators, and independent fresh-agent attempts for
review. The final task is **Rescue a quantum decoder's quarantined failures**.
The source paper is [Localized statistics decoding for quantum low-density
parity-check codes](https://arxiv.org/abs/2406.18655).

## Screening outcome

**Rejected: `remains_too_easy`.** All three substantive fresh-agent pilots
scored 1.00 without timing out. This is a review archive, not an accepted hard
ALE task. Each pilot used `ultima-alpha` with a 1,200-second limit.

| Version | Task mode | Reference score | Fresh-agent score | Timed out |
| --- | --- | ---: | ---: | --- |
| `v_01` | Regional logical-posterior repair | 1.00 | 1.00 | No |
| `v_02` | Syndrome-only calibration and temporal deployment | 1.00 | 1.00 | No |
| `v_03` | Recovery of curated quantum-decoder failures | 1.00 | 1.00 | No |

The initial `v_01/fresh_01` launch failed before model initialization and was
retried as `fresh_02`; that infrastructure failure is preserved but does not
count as a substantive screening round. See [status.json](status.json) and
the [screening summary](authoring/SCREENING_SUMMARY.md) for the full record.

## Where to start

- [Latest participant task](participant/v_03/TASK.md): objective, scientific
  semantics, interfaces, deployment limits, and required evidence.
- [Design rationale](authoring/DESIGN.md), [second revision](authoring/REVISION_V02.md),
  and [third revision](authoring/REVISION_V03.md): the task-selection history.
- `participant/v_NN/`: participant-facing task, inputs, and starter workspace.
- `solution/v_NN/`: known-good solution and saved reference evaluation.
- `evaluator/v_NN/`: behavioral evaluator and hidden cases.
- `attempts/v_NN/fresh_NN/`: submitted code, experiments, transcripts, run
  metadata, and the exact evaluator JSON.
- `authoring/`: construction scripts, independent scientific checks, and audits.

**Reviewer-only material is included.** Solutions, hidden labels, authoring
artifacts, and attempt transcripts must not be exposed to a fresh participant.
For a blind task attempt, share only the chosen `participant/v_NN/` directory.

## Re-running a saved evaluation

From this directory, in the original-compatible Linux environment:

```bash
python evaluator/v_03/evaluate.py --submission solution/v_03
python evaluator/v_03/evaluate.py --submission attempts/v_03/fresh_01
```

The original environment used CPython 3.10, NumPy 1.21.5, SciPy 1.8.0, and
`g++`. Saved native binaries, including the vendored reference dependencies,
target Linux x86-64; a different Python ABI or platform may require rebuilding
them. Vendored dependencies retain their upstream metadata and license files.
Each evaluator prints a JSON result with `passed`, `score`, and `reason`.

The authoring scripts and run metadata preserve original absolute paths.
Re-launching fresh agents requires the external allowlisted Codex runner and
model access from the original environment; those are not bundled here.
Disposable Python caches and empty agent-runtime directories are excluded
from the GitHub copy. Scientific inputs, outputs, and screening records are
otherwise preserved.
