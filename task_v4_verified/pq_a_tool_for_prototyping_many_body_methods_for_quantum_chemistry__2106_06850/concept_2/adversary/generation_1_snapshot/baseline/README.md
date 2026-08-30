# Random-search baseline

From `concept_2`, run:

```
bash baseline/run.sh --trials 10000 --seed 20260828 --output baseline/submission.json
python -I evaluator/evaluate.py baseline/submission.json --output baseline/evaluation.json
```

The identical starter shipped to participants is `participant/baseline/search.py`.
It samples symmetric Gaussian pair matrices, rejects unstable HF references,
solves CCSD, and retains the largest admissible population violation. It falls
back to the valid noninteracting example when no violation is found. A fallback
is not a successful witness. No private calibration seed or Hamiltonian is used.
