# Spectrally matched finite-chain layouts

`design.json` is the submission artifact. Each high/low pair permutes the same
twelve labelled fields, without modifying their values.

The search uses the supplied periodic Heisenberg Hamiltonian in the zero-total-Sz
sector (dimension 924), with the specified central rank slice and dynamical
fraction. It explores random permutations, locally mutated layouts, and layouts
with weakly coupled field clusters. Candidate comparisons include all three
field-strength scales and identical label-wise perturbations for both layouts.
This is a finite-system diagnostic experiment, not a thermodynamic phase claim.

## Validation

The supplied checker can be rerun from the participant directory:

```sh
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 \
PYTHONDONTWRITEBYTECODE=1 python workspace/check.py \
  ../attempts/v_1/design.json --output ../attempts/v_1/public_validation.json
```

`public_validation.json` records the public checker result. The `stress_*.json`
files and `holdout.log` record additional perturbation experiments; their
bootstrap probabilities are empirical diagnostics, not guarantees for the
unavailable committed hidden seeds. These reports explicitly retain any
remaining robustness misses.

The forty-draw set initially held out was subsequently used to compare three
finalists. Its final-artifact scores in `validation_summary.json` are therefore
selection-set results, not an untouched holdout. Broader perturbation testing
still exposes spectral-matching failures; this is the best-found public-valid
artifact, not a claim that all hidden robustness conditions have been achieved.

The implementation scripts and `observations.jsonl` retain the search and its
numerical observations. Numerical searches use four processes, each limited to
one numerical-library thread. Only `design.json` is needed by the evaluator.
