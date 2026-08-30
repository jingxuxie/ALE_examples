# Qiskit paper-seeded hardness discovery

Three concepts are built from arXiv:2405.08810 and documented official follow-ups. The synthetic workloads and calibration simulator are new task constructions, not claims to reproduce the paper's experimental data. Source provenance and the nine-concept screening record are under `authoring/`.

The completed experiment selects `concept_2` as `hard_verified_achievable`, retains `concept_1` as `hard_open_candidate`, and records `concept_3` as solved. Scores, private-search results, ratchet counts, and capability failures are in `FINAL_REPORT.md`; machine-readable decisions are in `status.json` and each concept's `status.json`.

| Directory | Verification mode | Submission |
| --- | --- | --- |
| `concept_1` | A: baseline improvement | Streaming compiler, `solution.py` and supporting files |
| `concept_2` | C: exact witness construction | Native-CX circuits in `solution.json` |
| `concept_3` | E: active experiment design | Line-JSON calibration controller, `solution.py` |

## Evaluation

Run from this directory, with Python 3.10+, NumPy, SciPy, Linux bubblewrap, and the system runtime libraries available:

```sh
OPENBLAS_NUM_THREADS=1 python3 concept_1/evaluator/evaluate.py /absolute/submission --output /tmp/phase-score.json
python3 concept_2/evaluator/evaluate.py /absolute/submission --output /tmp/witness-score.json
OPENBLAS_NUM_THREADS=1 python3 concept_3/evaluator/evaluate.py /absolute/submission --output /tmp/calibration-score.json
```

The submission code for concepts 1 and 3 executes in isolated namespaces with only participant assets, submission files, system libraries, and scratch space mounted. Hidden parameters, cases, private certificates, champions, and authoring tools are not mounted. Concept 2 only parses and checks the submitted JSON; it never executes submitted code. Sandbox startup is independently allowed up to 90 seconds; declared solver limits include submitted imports and computation.

The current concept-1 generation uses 82% mean / 80% worst-family cost-reduction targets. Its original generation and targets are preserved in `concept_1/adversary/generations/generation_0/`. To reproduce an old score with the current semantic evaluator, explicitly pass both its archived `evaluator/hidden/cases.json` and `targets.json` using `--cases` and `--targets`. Costs always use the unchanged supplied baseline portfolio, not a hidden optimal answer.

## Validation and isolation

```sh
OPENBLAS_NUM_THREADS=1 python3 concept_1/evaluator/selftest.py
OPENBLAS_NUM_THREADS=1 python3 concept_2/evaluator/selftests.py
OPENBLAS_NUM_THREADS=1 python3 concept_3/evaluator/selftest.py
```

Selftest reports, baseline scores, complete fresh-session logs, immutable scored submissions, private stress tests, and ratchet commitments are retained under each concept's `adversary/` and `evaluator/hidden/` directories. Only `participant/` and an initially empty `attempts/v_N/` directory are allowlisted for a tested agent. `authoring/run_tournament.py` invokes the user-supplied runner with `ultima-alpha`, a clean runtime without inherited conversation/history/memory, no network, read-only task assets, and a 3,600-second limit. It refuses nonempty output directories.

Private per-instance phase circuits establish cost headroom but are not represented as a generic passing compiler. The native-CX concept has a complete private feasible witness. Calibration's Fisher-information diagnostic is not a controller and does not establish target achievability. Empirical decisions are recorded only after fresh submissions are scored.
