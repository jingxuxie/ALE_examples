# Control witness

`pulses.json` is the submission: one fixed sequence of 24 two-group kick-angle
pairs, in radians. All 48 values lie in `[-pi, pi]`. The prescribed ZZ layers,
input state, and target are unchanged. No supporting code is executed by the
checker.

Artifact SHA-256:
`d96fc70c75500849200c31c19adfe1870b643a4a855684060a6eb92b61160df6`

## Validation of this artifact

- Public exact state-vector check: minimum fidelity **0.9829961360977465**
  over all 15 public scenarios; nominal fidelity **0.9996517437402124**.
- Expanded check: minimum fidelity **0.9590763502134633** over 41,039
  scenarios: 79 public/structured cases, every one of the 32,768 endpoint
  combinations of the 15 calibration variables, and 8,192 seeded random cases.
- The expanded check uses the exact free-fermion covariance representation.
  Independent 4096-amplitude simulation cross-checks 174 selected scenarios,
  including the lowest-fidelity cases. Maximum discrepancy is `8.22e-15`;
  their state-vector minimum is **0.9590763502134589**.
- An additional 128 bounded, local adversarial optimizations over continuous
  calibration variables find no lower value. Every resulting scenario is
  checked with the supplied state-vector simulator.

These are finite numerical checks, not a certificate over the continuum or a
claim to have accessed the private test suite. Detailed final results are in
`public_score.json`, `validation.json`, and `adversarial_validation.json`.

## Supporting tools

`gaussian.cpp` implements covariance propagation and analytic pulse gradients.
Its fidelities and gradients were cross-checked against the supplied simulator
and finite differences. `search.py`, `multistart.py`, and `global_search.py`
implement bounded multistart, soft-minimum fidelity optimization. The final
sequence is the checkpoint labeled `global_best_6.npy`.

From this directory, using the participant assets in their original location:

```bash
g++ -O3 -march=native -shared -fPIC -fopenmp gaussian.cpp -o gaussian.so
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python ../../participant/workspace/score_public.py --submission .
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python validate.py --vertices --samples 8192
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python adversarial_validate.py
```

The covariance kernel uses at most four CPU threads. Search scripts overwrite
`pulses.json`; running validation scripts does not change it.
