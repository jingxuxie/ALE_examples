# Paper-seeded hardness discovery

**Primary retained task: `concept_1` — hard_verified_achievable.**
`concept_2` is additionally retained as a hard_open_candidate; `concept_3` is
solved and not retained. See `FINAL_REPORT.md` and `status.json` for scores and
empirical decisions. Nine seed concepts were screened; exactly three were
built using modes E, B, and D.

Seed: Many-Body Expanded Full Configuration Interaction. I. Weakly Correlated
Regime, arXiv:1807.01328. These are explicit seniority-zero paired-electron
model tasks, not reproductions of ab initio molecular or unrestricted FCI
calculations. Source and selection audits are in `research/`.

## Current packages

| Concept | Canonical generation | Task | Evaluator |
| --- | ---: | --- | --- |
| Active experiments | 2 | `concept_1/participant/TASK.md` | `concept_1/evaluator/evaluate.py` |
| Robust counterexample | 3 | `concept_2/participant/TASK.md` | `concept_2/evaluator/evaluate.py` |
| Prediction, archival solved task | 1 | `concept_3/participant/TASK.md` | `concept_3/evaluator/evaluate.py` |

Each concept includes participant assets, a weak baseline, hidden evaluator,
actual fresh attempts, champions, adversarial evidence, and final status.
Selected versioned packets remain immutable under `adversary/ratchet_1` or
`adversary/ratchet_2`. Their frozen statuses describe prelaunch readiness;
canonical root statuses describe final outcomes. Historical passers and
original canonical packets are preserved, not overwritten.

## Strict participant boundary

Give a solver **only the chosen `participant/` directory read-only and a new
empty writable output directory**. Never expose this whole output tree,
evaluator/hidden data, paper/repository artifacts, previous submissions,
champions, private portfolios, root status, or this README. In particular,
`concept_1` has a private known passing policy that must remain inaccessible.

`research/launch.py` uses the supplied allowlisted runner, ephemeral
`ultima-alpha`, disabled web search, closed stdin, and an enforced 3,600-second
construction timeout. Manifests record input hashes, initial emptiness, and
read-only access. The final counterexample has two independent attempts on
identical frozen assets. Attempt index and task generation are separate.

## Privileged reproduction

Python 3, NumPy, and SciPy suffice for active/counterexample evaluation.
Prediction baseline training also uses scikit-learn. Active evaluation requires
bubblewrap namespace permissions and fails closed without isolation. Static
artifact evaluators execute no submitted code. Use one BLAS thread.

```bash
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
python -B concept_1/evaluator/evaluate.py --submission concept_1/participant/baseline --output /tmp/c1_baseline.json
python -B concept_1/evaluator/evaluate.py --submission concept_1/attempts/v_2 --output /tmp/c1_fresh.json
python -B concept_1/evaluator/evaluate.py --submission concept_1/adversary/ratchet_1/adversary/portfolio/candidate_a --output /tmp/c1_passing.json
python -B concept_2/evaluator/evaluate.py --submission-dir concept_2/participant/baseline --report /tmp/c2_baseline.json
python -B concept_2/evaluator/evaluate.py --artifact concept_2/attempts/v_4/witness.json --report /tmp/c2_fresh.json
python -B concept_3/evaluator/evaluate.py concept_3/attempts/v_1/predictions.npz --output /tmp/c3_fresh.json
python -B concept_1/adversary/ratchet_1/evaluator/verify_freeze.py
python -B concept_2/evaluator/hidden/test_packet.py
python -B -m unittest discover -s concept_3/evaluator/tests -v
python -B research/audit.py --require-complete
```

Baseline generators and detailed interfaces remain inside each participant
packet. Full historical freezes are verified at their immutable versioned
packets, rather than against subsequently updated lifecycle metadata. An
initial stdin-only runner startup failure is archived in
`research/runner_infra/` and is not scientific hardness evidence.
