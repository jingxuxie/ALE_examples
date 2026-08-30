# Qualtran paper-seeded hardness discovery

Three concepts are built from arXiv:2409.04643 and inspected official follow-ups.
The source snapshots, private constructive witnesses and search data are NOT
participant assets. Task definitions live only under each `participant/` tree.

| Concept | Primary verification mode | Static submission |
| --- | --- | --- |
| 1: Bloq scheduling | A: baseline improvement | `schedules.json` |
| 2: Silent GQSP failure | B: counterexample/falsification | `counterexample.json` |
| 3: Coherent lookup | C: witness/design construction | `circuits.json` |

## Scoring

Each evaluator uses the same command contract and never executes submitted code:

```
python3 concept_1/evaluator/evaluate.py --submission /absolute/submission --report /tmp/score.json
python3 concept_2/evaluator/evaluate.py --submission /absolute/submission --report /tmp/score.json
python3 concept_3/evaluator/evaluate.py --submission /absolute/submission --report /tmp/score.json
```

The numerical evaluator needs NumPy and mpmath; the other evaluators need only
Python 3.10+. Exact installed versions are recorded in `authoring/environment.json`.
`requirements-evaluation.txt` pins the numerical dependencies for Python 3.10.
Numerical scores are tied to the recorded binary64 environment; the independent
circuit expansion uses 80 decimal digits and is cross-checked at 120 digits.
Each participant has its own baseline and public checker; commands are in its
interface document. Current evaluator targets may differ from earlier ratchet
generations. Old participant/evaluator trees are immutable archives under
`concept_N/adversary/generations/generation_G/`; use that generation's evaluator
to reproduce an old score. `authoring/score_completed.py` handles this selection
automatically and snapshots completed artifacts before scoring them.

## Isolation and evidence

`authoring/run_tournament.py` invokes the unchanged user-supplied allowlisted
runner with `ultima-alpha`, fresh runtime/auth context, no inherited sessions or
memory, four CPU affinity slots and a 3,600-second construction limit.
An 8 GiB per-process address-space ceiling is enforced; aggregate RSS is not measured.
Termination has a ten-second cleanup grace, recorded separately from the cutoff.
Only the specific read-only participant directory and initially empty writable attempt
directory are mounted for tools. A private user/mount/PID root prevents host
temporary-directory mount failures; the original Codex sandbox remains enabled.
Controller network access serves the model API, while child-tool network access
is denied. Preflight checks cover allowed reads/writes, forbidden hidden and
runtime credential reads, participant write denial, network denial and PTYs.

The initial scheduling run lacked PTY support and is explicitly excluded as
infrastructure-invalid. Its replacement receives a full fresh budget. No failure
of a broken environment is evidence of task hardness. Full logs, per-generation
hash freezes, scored submissions and search provenance remain private under
`adversary/` and `authoring/`. Final decisions belong in per-concept `status.json`
and the root report, not inferred from a missing file in an active attempt.

## Validation

Scheduling has independently implemented live-edge and integer-summary checkers,
exhaustive small-graph tests and a private passing schedule. Lookup has row-wise,
packed-bit and independently synthesized ANF validation plus compact private
circuits. Numerical checks use exact dyadic autocorrelation certificates,
bit-for-bit upstream extraction tests and independent 80/120-digit circuit
expansion. A passing witness in an old or larger-degree numerical domain does
not demonstrate achievability of a later compact-degree ratchet.

`authoring/audit_package.py --require-complete` replays every current baseline,
checks all archived/current hash freezes, and verifies fresh-run metadata and
completed credential cleanup. `authoring/finalize.py` refuses active attempts
and derives decision records only from evaluated artifacts. Neither script
modifies participant or evaluator assets.
