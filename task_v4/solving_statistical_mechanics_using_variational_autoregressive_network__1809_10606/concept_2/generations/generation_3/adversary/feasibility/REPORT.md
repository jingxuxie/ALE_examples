# Private generation-3 feasibility portfolio

No passing witness was found. General attainability remains UNKNOWN.

## Scope and budget

All new artifacts are confined to this private feasibility directory. No fresh attempt was read, no participant/evaluator/spec/status was edited, and release hashes were rechecked.
The requested 20-minute window began at 2026-08-28 21:17:49 UTC. Main optimization stopped when its fixed 21:37:00 UTC deadline was reached, followed only by evidence finalization; numerical and official checks are archived.

## Portfolio

- Seed 202608282118: 119 binary-disorder draws, 29 accepted gauge-distinct models, 56 exact antipodal training basins.
- 45 completed coupled refinements on 22 bond instances and 29 distinct causal orders; 50 per-trial official reports.
- Conditional equilibrium weights on antipodal ground components plus single-flip neighborhoods or low-energy Hamming balls; bounded convex weighted logistic row fits; row-major, column-major, min-fill, BFS, and randomized orders.
- Exact reverse-KL plus 20 times missed-sector mass initial refinement, variance minimization, and ambient-gradient-penalized refinement were all included. Beta was optimized continuously within [1,3].
- Separate seed 202608282132 screened additional causal orders for newly sampled disconnected-component models; it did not reuse the completed champion's optimization trace.
- Fitted, best-score, and final iterates are saved separately. These are local, time-limited searches, not global minima or certificates.

## Best officially checked candidate

Source: `order_sweep/trials/000/witness.json`; canonical copy: `final_best/witness.json`; report: `final_best/official_report.json`.
Valid: True; passed: False; score: 0.142444478343.

| Metric | Measured | Frozen gate |
|---|---:|---:|
| Entropy | 3.24185047327 | >=3 |
| Reverse KL | 0.823791514937 | >=0.4 |
| Total reward variance | 0.230174969303 | <=0.05 |
| Ambient gradient infinity | 0.0210608374217 | <=0.003 |
| Dimensionless mean-energy error/spin | 0.0158341889428 | <=0.02 |
| Target sector probability | 0.396438486022 | >=0.35 |
| Proposal sector probability | 3.40749860084e-05 | <=0.001 |

Failed gates: reward_variance, gradient_infinity. Minimum binary conditional: 0.0100000000099.

## Validation and interpretation

Self-checks passed: True. Half-enumeration versus frozen full enumeration agreed within 5.46e-14; 110 central-difference gradient checks had maximum objective discrepancy 2.31e-08; 180 direct-sector checks agreed within 2.22e-16.
Frozen file differences: []. Official generation-3 specification SHA256: `dd13c731a15fa61f8a2c3e92602de9671ad5e2c62c66f76d7cc47b06a46d618f`.
An unsuccessful bounded portfolio does not establish global infeasibility, nor does it invalidate either previously solved generation. The frozen generation-3 task and its fresh evaluations remain main-controlled.

## Reproduction and artifacts

Run `python -B portfolio.py --deadline-utc <future-UTC-ISO-time> --seed 202608282118` from a separate authorized copy for the main portfolio. Time-limited concurrent runs need not reproduce identical terminal iterates; all exact retained JSON witnesses are independently reproducible with the frozen evaluator.
`models.json`, `basin_pool.json`, `trials.json`, `order_sweep/`, `official_trial_reports.json`, `selfcheck.json`, and `manifest.json` retain instances, basins, row-fit gap diagnostics, seeds, stopping conditions, and verification evidence.
