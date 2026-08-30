# Spin-register identification controller

Run `python3 solve.py`. The controller reads and writes the newline-delimited JSON protocol on standard input/output. It needs only Python 3, NumPy, and SciPy; it does not load any model, data, or simulator files.

The controller uses two fixed, information-optimized preparations, fits the exact coherent dynamics and independent detector errors, then chooses the third experiment adaptively. The design accounts for both local parameter uncertainty and competing likelihood modes. Analytic Hamiltonian derivatives, bounded multistart maximum likelihood, and recovery restarts make the inference robust to mixed-sign fields and frustration.

It requests exactly three experiments. Numerical libraries use one thread, and inference includes CPU and wall-time guards.

## Local validation

- 90 simulated development/synthetic cases: mean normalized RMSE **0.012311**, maximum **0.022587**.
- Lowest mean regime score: **0.987106**.
- All three supplied development examples pass the executable protocol test.
- Maximum observed inference CPU time in the 90-case run: **13.002 seconds**; measured protocol-test peak memory: approximately **62 MB**.
