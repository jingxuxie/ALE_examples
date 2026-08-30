# L14 dynamical spin fraction submission

Run `python3 predict.py` without arguments. It loads all assets, flushes `READY`, reads one JSON request, writes one JSON response, and exits. No input fields are available or used before `READY`.

## Predictor

The submitted model averages three independently trained neural networks with stochastic weight averaging. Each network has 521 inputs, hidden layers of 256 and 128 SiLU units, and a sigmoid output. Inputs describe centered ordered fields, local barriers, multistep resonances, Fourier invariants, block structure, and near-resonant pairs. Features respect translation, reflection, global spin inversion, and uniform field shifts. Inference uses algebraic descriptors only: no Hamiltonian diagonalization or sample lookup.

Runtime requires Python, NumPy, SciPy, and the supplied assets. PyTorch and scikit-learn are training/test dependencies only. Native descriptor extraction and quantile interpolation are precompiled for Linux x86-64; `bash build.sh` rebuilds them with GCC/G++ and system BLAS/LAPACK. Numerical libraries use one thread; inference uses at most four worker threads.

Required runtime files: `predict.py`, `model.pkl.gz`, `native_features.py`, `libnative_features.so`, `transforms.py`, and `fast_transform.so`.

## Training and validation

The final fit uses all 2,400 public labels and simulated realizations numbered 0 through 1599. Simulations use the supplied exact middle-third eigenstate definition, seed `280820261951`, eight workers, and one BLAS thread per worker. Realizations 1600 through 1799 remain outside the final fit and preprocessing fit. `simulated.jsonl` preserves the generated labels and ordered fields.

`validation_metrics.json` records held-out accuracy and `runtime_test.json` records streaming tests with four-core affinity and a 2,048 MiB address-space limit. These are local validation results, not hidden-test scores.

Final results on 200 untouched simulations: overall RMSE **0.01982**, worst-family RMSE **0.02219**. Five 320-case streaming tests take **0.122–0.454 seconds** after `READY`; startup takes **0.650–1.567 seconds**. A separate test using only the six runtime assets also passes. Timing cases include 120 public fitting examples, so their diagnostic RMSE is not a held-out accuracy estimate.

To reproduce the final fit from the retained simulation bank:

```sh
export SRC=/path/to/participant
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
bash build.sh
python3 prepare.py
python3 train_neural.py --prefix final --variant algebra --width 256 --seeds 3 --final
python3 bundle.py --prefix final --neural-variant algebra --width 256 --neural-weight 1
python3 -m unittest test_features
python3 test_submission.py --cases runtime_cases.jsonl
```
