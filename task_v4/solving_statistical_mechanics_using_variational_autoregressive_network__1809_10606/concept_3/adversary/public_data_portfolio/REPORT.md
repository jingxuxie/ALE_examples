# Public-data-only attainability portfolio

Known achievable: **yes**.

All variants were preregistered, fitted from participant observations and public priors only, and hash-sealed before any trusted scoring.
No hidden parameters, generation seeds, query labels, or fresh submissions were read by the fitter. No scores informed training or tuning.

| Variant | Fit/control seconds | Mean KL | Worst-family KL | Max TV | Pass |
|---|---:|---:|---:|---:|---|
| midpoint_prior | 0.08 | 0.30821521 | 0.41725990 | 0.44774510 | False |
| empirical_log_bridge | 0.01 | 0.00920642 | 0.01231653 | 0.08540248 | True |
| latent_fit_weak | 187.57 | 0.00075270 | 0.00088750 | 0.02138674 | True |
| latent_fit_strong | 39.87 | 0.00588580 | 0.00674957 | 0.05676325 | True |

Fixed gates: mean KL <= 0.020; worst-family mean KL <= 0.035; maximum TV <= 0.120.

The latent fits optimize the exact visible marginal likelihood of all 16,384 configurations, summing over adjacent hidden spins with a batched transfer recursion.
Both start independently at the public bound midpoints. Normalized quadratic penalties have fixed coefficients 0.001 and 0.01. CPU affinity uses four cores; each fit has a predeclared 360-second cap.
The other variants are an unfitted public-prior midpoint control and a Jeffreys-smoothed empirical log-probability temperature bridge with local field reweighting.

See PREREGISTRATION.json, STARTED.json, implementation_checks.json, OUTPUTS_FROZEN.json, individual fit_report.json files, and scores/*.json for the audit trail.
