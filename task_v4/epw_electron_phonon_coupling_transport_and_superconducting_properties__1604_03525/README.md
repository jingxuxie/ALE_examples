# EPW-seeded hardness discovery

This private task-generation package contains three reduced electron–phonon
model problems seeded by arXiv:1604.03525. These are not first-principles EPW
calculations or claims about experimentally measured materials.

| Directory | Primary verification mode | Submission |
|---|---|---|
| `concept_1` | D — hidden spectral prediction | `solve.py` and optional trained assets |
| `concept_2` | A — collision-event baseline improvement | `solve.py` and supporting files |
| `concept_3` | B — matched-observable transport falsification | `witness.json` |

## Trust boundary

Only `concept_N/participant/` and an initially empty writable output directory
may be provided to a fresh solver. Everything else is privileged: evaluator
labels and seeds, research, adversarial searches, previous submissions,
champions, and this documentation. Do not mount the package root for a solver.
Prior submissions and trained weights were not supplied in ratcheted public
baselines. `authoring/isolation_audit.json` records filesystem and network probes.

## Running

The tested environment uses Linux, Python 3, NumPy, SciPy, threadpoolctl,
`bubblewrap`, and `prlimit`. Keep `authoring/sandbox.py` adjacent to the three
concepts: the executable evaluators import it to run untrusted submissions with
allowlisted mounts, no network, and resource limits. It deliberately fails
closed if that isolation cannot be established.

The executable memory guard is an address-space limit (`RLIMIT_AS`), not a
resident-set measurement. The spectral participant wording did not explicitly
distinguish these. Its final Torch submission hits that distinction; the final
report therefore separates the official execution failure from an unchanged-code,
memory-relaxed diagnostic of scientific accuracy. The latter is never recorded
as an official pass.

From this package directory, score a staged submission with:

```sh
/usr/bin/python3 concept_1/evaluator/evaluate.py --submission /absolute/submission --output /tmp/spectral-score.json
/usr/bin/python3 concept_2/evaluator/evaluate.py --submission /absolute/submission --output /tmp/transport-score.json
/usr/bin/python3 concept_3/evaluator/evaluate.py --submission /absolute/submission --output /tmp/witness-score.json
```

For executable baselines, use `concept_1/participant/baseline` or
`concept_2/participant/baseline` as the submission directory. Concept 3 includes
a pre-generated `participant/baseline/witness.json` and its runnable generator.
Evaluator commands must run in a host context permitting their own bubblewrap
namespaces; do not weaken isolation to work around a permission failure.

Fresh attempts are launched through `authoring/run_attempt.py`, which invokes
the required `run_allowlisted_codex.sh` with model `ultima-alpha`, a read-only
participant mount, and a 3,600-second deadline. Trial logs, frozen before/after
hashes, and score reports are in `attempts/` outside the solver's output mount.

## Evidence

`research/concepts.md` records nine considered concepts and source provenance.
Each `status.json` identifies its final generation and authoritative score paths.
The generation-1 `evaluator/baseline_score.json` files are historical: for
ratcheted concepts, use `adversary/generation_2_baseline_score.json` instead.
Champion archives preserve earlier participant/evaluator versions. Label-oracle
scores and over-budget identity tests validate evaluators only; they do not
demonstrate an achievable participant solution. One externally terminated
spectral infrastructure trial is explicitly excluded from hardness evidence.

Final empirical decisions are recorded in `status.json` and `FINAL_REPORT.md`.
