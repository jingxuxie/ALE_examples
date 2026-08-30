# Submission

`predictions.json` contains outcome-one probabilities for every supplied query.

The model implements exactly the disclosed two-state classical environment,
maintains its correlations with the weighted qubit Bloch vectors, and includes
gate-dependent bias and damping, two-component pulse memory, and smooth drift.
Every device's 54 physical parameters are fitted within the published bounds by
binomial maximum likelihood. Fits progress from short circuits to all training
circuits before incorporating the development counts for the final predictions.

The C++ simulator has analytical reverse-mode derivatives. `validate.py` checks
its predictions against an independent SciPy rotation implementation and all 54
derivatives against central differences. `generate.py` repeats the independent
forward-model check on long query circuits and validates the submission format.

`development_heldout.json` uses only the training fits, so the supplied development
scorer can evaluate genuinely held-out predictions. `diagnostics.json` includes
these count-based diagnostics and local parameter-uncertainty propagation to the
query circuits. These estimates are not private exact-probability scores.

Reproduction, with the supplied participant assets in their original location:

```sh
g++ -O3 -march=native -fopenmp -shared -fPIC simulator.cpp -o simulator.so
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=2 python validate.py
for device in 0 1 2 3; do
  OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=2 python fit.py --device "$device" --include-development
done
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=2 python generate.py
```
