# Joint uncertainty from signed Monte Carlo replicas

Implement `workspace/solve.py` to recover nonlinear observables and their full sampling covariance from correlated, signed measurements collected by independent replicas. Preserve sign normalization, alignment, replica boundaries, partial batches, and cross-observable covariance at every requested blocking scale.

Run as `python3 solve.py --input INPUT.json --output OUTPUT.json`. Write the result to the supplied output path. The complete statistical and JSON contract is in `input/CONTRACT.md`; `input/example.json` is a tiny unlabeled input. The starter is an intentionally weak iid, diagonal-error baseline.

Python 3, NumPy, and SciPy are available. Budget: 120 seconds and 2 GiB per input. Accuracy of joint covariance and replica results matters independently of mean accuracy; a mean-only or diagonal-only answer is insufficient.
