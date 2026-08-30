# Adaptive correlated-Ramsey calibration

## Run

```sh
python -u solution.py
```

The program implements the task's JSONL interface. As specified by the task, the
runtime must provide the public `input/simulator.py` alongside these files.
Python, NumPy, and SciPy are the only numerical dependencies.

- `solution.py` handles input/output, single-thread settings, deadline protection,
  and prompt successful termination after the estimate.
- `calibration.py` contains the experiment designer and estimator.

No training data, saved episode state, network access, or additional assets are
needed at runtime.

## Method

1. Measure SPAM and obtain global frequency candidates using nonuniform Ramsey
   times. Additional measurements are requested when competing frequency aliases
   have insufficient likelihood separation.
2. Resolve the coupling using short, phased spectator-conditioned measurements.
3. Maintain a Bayesian posterior over the disclosed prior families, including
   both correlation-sign components of the close-coupled family. Heavy-tailed
   importance proposals are corrected using the exact binomial likelihood and
   prior supports.
4. Choose subsequent measurements by expected posterior error reduction. The
   design includes the actual 588-probability prediction grid, not just a local
   parameter-information approximation. A diverse shortlist is evaluated using
   the complete distribution of possible binomial counts.
5. Select the final estimate using the published score's parameter and predictive
   terms. All returned parameters are finite and clipped to the allowed bounds.

The normal design uses all 48 queries and 6,144 shots. A deadline fallback may
terminate earlier rather than violate the runtime limit. Standard output contains
only protocol responses.

## Verification

- The supplied public runner passed all three episodes: **91.86 mean** and
  **88.67 worst-family score**. See `public_report.json`.
- 135 locally simulated episodes from the supplied priors averaged **91.93**;
  their lowest family mean was **89.99**.
- A separate 2,000-episode acquisition test found no frequency errors above
  0.1 MHz after acquisition. Six prior-boundary cases were also checked.
- See `validation_summary.json` for test summaries, budget checks, and source
  hashes. Synthetic accuracy checks ran in-process; the public runner separately
  checked the executable interface and single-CPU resource limits.

These are public/local tests, not results on the hidden episodes.
