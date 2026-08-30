# Detector-channel calibration submission

Run the standalone entry point with `/usr/bin/python3 solution.py`. It reads the
specified JSON-lines protocol from stdin and writes only flushed protocol messages
to stdout. NumPy and SciPy are its only external dependencies. No training files,
external numerical helpers, or saved state are needed at evaluation time.

## Method

- Evaluate the exact joint syndrome likelihood using a Walsh transform, preserving
  the shared shot-mode mixture and alternative detector footprints.
- Use a small pilot across informative interventions, followed by three rounds
  of adaptive shot allocation and bounded maximum-likelihood fitting.
- Optimize the mean predicted family-wise log-rate uncertainty using per-action
  Fisher matrices, accounting for all shots already collected.
- Integrate the final posterior in log-rate coordinates with bounded,
  quasi-Monte-Carlo importance sampling. Return the geometric posterior means,
  appropriate for squared log-rate loss.
- Spend exactly 40,000 shots while respecting query size and query count limits.
  Numerical libraries are explicitly restricted to one thread.

## Validation artifacts

`final_local_0.json` through `final_local_5.json` contain results from the provided
`input/local.py` driver. These runs impose the 60-second CPU and 3-GiB address-space
limits on the worker. `final_summary.json` pools their regime/family errors using
the task's scoring convention. Public training results are not an official
hidden-suite result.

The six supplied episodes give a mean regime/family log RMSE of **0.05043559**
and a maximum of **0.06778660**, below the respective **0.055** and **0.095**
thresholds. All six use exactly 40,000 shots. The analytic probabilities and
derivatives also agree with the supplied model and finite-difference checks.

The benchmark and comparison scripts and their JSON/log outputs retain the local
allocation, numerical, repeated-sampling, and randomized-rate experiments. They
are development artifacts and are not imported by `solution.py`.
