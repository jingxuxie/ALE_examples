# Three-probe spectroscopy controller

Run `python3 solve.py` using the newline-delimited JSON protocol in the public
task. The only submission dependency is `model.py`; NumPy 1.21.5 and SciPy
1.8.0 suffice. No training data, parameter lookup tables, device identifiers,
hidden-case files, network access, or state shared between devices are used.

## Method

1. Measure preparations 21 and 7 at times 1.1 and 2.0, respectively. Midpoint
   phases are generated reproducibly from a fixed, device-independent seed.
2. Jointly fit all 20 unknown parameters, including all six readout errors,
   using full 64-outcome multinomial deviance and exact analytic derivatives.
   Twelve initializations explore distinct likelihood modes.
3. Generate 240 admissible candidate quenches and kicks. Choose the third
   experiment by minimizing the likelihood-weighted trace of the inverse
   expected Fisher information over the retained plausible modes.
4. Refit the full three-experiment data from retained modes and twelve
   perturbed/global starts, then report the best bounded likelihood estimate.

`model.py` reuses the forward model, analytic Jacobian, and deviance fitter from
the permitted public champion. The longer first two probes, multimodal search,
and final adaptive design are implemented in `solve.py`. CPU-time guards bound
restart work. Numerical libraries use one thread, below the four-thread limit.

## Validation

From the concept root, the authoritative command is:

```sh
/usr/bin/python3 -B generations/generation_1/evaluator/evaluate.py \
  --submission generations/generation_1/adversary/portfolio \
  --output generations/generation_1/adversary/portfolio_score.json --jobs 3
```

Run this outside a nested sandbox so the evaluator can create its own bwrap
network namespace. The evaluator mounts only system libraries, the public
participant directory, the submission, and its scratch directory.

The scored controller is frozen. Score reports and independently generated
synthetic cases remain outside the submission directory. Passing the finite
evaluation suite demonstrates its achievability, not global identifiability
over every admissible parameter vector.
