# Generation 2 is frozen and ready

**Generation: `population-witness-v2-dad`; ratchet count: one.** Main may launch
both full one-hour ultima-alpha replicates. This worker launches no agents.

Copy only the active `concept_2/participant/` tree into completely fresh isolated
workspaces. No generation-one attempt, champion, optimization code, private
artifact, evaluator, or author record may be exposed. The active participant
and evaluator hashes are in this directory's `freeze.json` and
`evaluator_freeze.json`. Root generation-one manifests remain historical.

The sole added scientific gate is final-density
`DAD = ||gamma-gamma.T||_F / sqrt(3) <= 0.001`. This is not a max-entry norm.
The population-violation target remains 0.02, and every original threshold,
Hamiltonian domain, score, and 64-step continuation constraint is unchanged.
TASK explicitly challenges a task-supplied stronger heuristic, not a theorem
or a guarantee attributed to arXiv:2106.06850 or arXiv:2503.20006v2.

Both old fresh witnesses fail **only** the new bound: their DADs are
0.2779481391723832 and 0.38214541754498366. Their original scores and all
generation-one snapshots/champion files are unchanged. The new evaluations live
only in this generation-two directory.

Basic audits pass: 12 DAD identity/orthogonal-invariance cases, 16 independent
oracle comparisons, N=2 CCSD=FCI and derivative checks, 44 malformed/security
cases, and five DAD boundary/nonfinite cases. The unchanged 10,000-draw random
baseline, using the new API gate, scores zero. The zero-interaction example is
still admissible and nonpassing.

Current achievability decision: **verified private generation-two witnesses**.
Two post-freeze private warm-start searches passed the isolated CLI evaluator:
population violation 0.02052025499 with DAD 0.00011982039, and population violation
0.02193328581 with DAD 0.00048860675. Both pass all unchanged endpoint and path
constraints. Their search runtimes were approximately 87 seconds and 5 seconds
using privileged generation-one solutions and analytic-gradient code. These are
not fresh participant solves and do not establish fresh-agent difficulty.
They do establish feasibility of the ratchet. No thresholds changed after freeze.

The private artifacts and full reports are in `worker_feasibility_champion_high/`
and `worker_feasibility_replicate1_high/` here. Never expose them or their source
seeds to generation-two agents.

Official evaluation from `concept_2`:

```
python -I evaluator/evaluate.py /absolute/attempt/submission.json \
  --submission-dir /absolute/attempt --output /trusted/generation_2_report.json
```

Do not follow submission symlinks in the orchestration layer. The evaluator
rejects symlink path components and files outside the declared submission
directory and recomputes DAD independently from the actual lambda density.
