# XMDS2-seeded hardness discovery

The selected task is `concept_3`, a verified-achievable coherent-control design
challenge. `FINAL_REPORT.md`, `FINAL_REPORT.json`, and `status.json` contain the
empirical decisions, scores, ratchet counts, and evidence locations for all three
concepts. `authoring/DECISION_PROTOCOL.md` records the classification rules and
the treatment of time limits, dispatcher errors, and numerical uncertainty.

## Distribution boundary

Release only a concept's `participant/` directory to a tested agent, together
with an empty writable output directory. Evaluators, hidden data, source archives,
private passing artifacts, earlier attempts, champions, adversaries, and generation
snapshots are organizer-only. The recorded trials use the supplied allowlisted
runner; their commands, cutoff hashes, and integrity audits are retained.

## Scoring environment

The reference environment is Python 3.10.12, NumPy 1.21.5, and SciPy 1.8.0.
Concept 1 additionally requires Linux bubblewrap with usable user namespaces.
Its executable submission is isolated; concepts 2 and 3 read bounded regular JSON
files and never import submitted code. No XMDS2 installation is required.

Run from this directory, using one numerical-library thread:

```sh
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
/usr/bin/python3 -B concept_1/evaluator/evaluate.py concept_1/participant/baseline --output /tmp/xmds2_A_baseline_score.json
/usr/bin/python3 -I -B concept_2/evaluator/evaluate.py --submission concept_2/participant/baseline/champion.json --output /tmp/xmds2_B_baseline_score.json
/usr/bin/python3 -I -B concept_3/evaluator/evaluate.py --artifact concept_3/participant/baseline/control.json --output /tmp/xmds2_C_baseline_score.json
```

Baseline rejection is expected at the final targets; inspect both `valid` and
`passed`. Run concept 1 from a host where namespace creation is permitted rather
than nesting it inside an incompatible restricted sandbox. B's final grader has
1500-second wall and 900-second CPU limits; C's trusted numerical grading may take
several minutes. These grading times do not extend the one-hour development limit.

Generation snapshots preserve build-time status and freeze manifests. Their
`outcome.json` files record completed tournaments without rewriting frozen
metadata. `tested_participant/` and `tested_evaluator/`, when present, are the
exact archived published copies. Original attempt directories are not modified
by later searches. Recheck the final integrity audit with:

```sh
/usr/bin/python3 -B authoring/audit_attempt_integrity.py --require-complete
```
