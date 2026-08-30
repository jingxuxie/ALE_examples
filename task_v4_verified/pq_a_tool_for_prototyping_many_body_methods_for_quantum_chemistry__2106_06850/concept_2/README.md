# Concept 2: a Hamiltonian-derived CCSD density counterexample

Primary mode: **B — counterexample/falsification**. Scientific seed:
Rubin and DePrince, arXiv:2106.06850v3, unrelaxed CCSD lambda RDMs. The challenged
screening heuristic is supplied by this task, not attributed to the paper.

## Participant boundary

Only `participant/` is participant-visible. Its ten files are frozen under
`freeze.json`, generation `population-witness-v1`. They include a concise task,
the complete quantitative contract, the numerical oracle, one valid nonwitness
example, and a runnable random-search baseline. The private witness, calibration
searches, evaluator, and author records must remain outside fresh workspaces.
The main session launches fresh agents; this worker launches none.

## Witness and outcome

The fixed system is three fermions in six spin-orbitals, with 120 independent
real two-body parameters and a prescribed canonical-Fock counterterm. Search for
a material **real-orbital population** violation in the unrelaxed CCSD lambda
1-RDM while maintaining a locally stable canonical HF reference, exact CC
stationarity, energy error <= 1e-4, squared ground-state fidelity >= 0.999,
well-conditioned response, and the documented 64-step ground-connection certificate.

The score is the largest population distance outside `[0,1]`; the pass threshold
is 0.02. A private author-side witness scores approximately 0.025, with energy
error 8e-5 and fidelity 0.999999897. It is **achievability evidence, not a fresh
participant solution**. Final difficulty must be judged from the main session's
separately isolated one-hour attempt, not inferred solely from this private result.

## Commands

From this directory:

```
bash baseline/run.sh --trials 10000 --seed 20260828 --output baseline/submission.json
python -I evaluator/evaluate.py baseline/submission.json --submission-dir baseline --output baseline/evaluation.json
OPENBLAS_NUM_THREADS=1 python evaluator/hidden/audit.py
OPENBLAS_NUM_THREADS=1 python evaluator/hidden/robustness.py
```

The JSON-only evaluator independently reconstructs full-Fock fermion operators,
stationarity, lambda, HF curvature, FCI constraints, and the path certificate. It
uses a bounded worker, strict finite/schema validation, and descriptor-based
no-symlink input reads. See `evaluator/README.md` for the submission-directory
security boundary. `status.json` and `FILES.md` summarize outcomes and locations.
