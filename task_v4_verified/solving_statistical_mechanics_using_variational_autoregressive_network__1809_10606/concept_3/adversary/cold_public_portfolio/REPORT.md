# Cold public-data portfolio: final bounded result

**No feasibility pass established: 0/10 preregistered artifacts meet all three gates.**

Eight public exact-likelihood point fits and two unchanged public-trained controls were completed and hash-frozen before cached exact labels were opened. All ten artifacts satisfy the public NPZ schema adapted to the 48 preregistered queries. Scoring occurred once; no score-driven retuning, hidden-model access, fresh-attempt access, gen2 edits, or full-posterior control duplication occurred.

## Selected artifact

- Variant: `frozen_weak_control` (the unchanged public-trained weak control).
- Mean KL: 0.0132268545947 <= 0.02.
- Worst-family mean KL: 0.0186545496491 <= 0.035.
- Maximum TV: 0.205090310027 > 0.12: **fails**.
- Artifact: `best_predictions.npz`; parameter copy: `best_parameters.npz`.
- Selection followed the preregistered lowest-mean-KL fallback rule because no candidate passed.

## All frozen results

| Variant | Mean KL | Worst-family KL | Maximum TV | Pass |
|---|---:|---:|---:|---|
| refined_weak_1e3 | 0.01323154 | 0.01866901 | 0.20530311 | False |
| regularized_3e4 | 0.02899762 | 0.04932293 | 0.43188145 | False |
| regularized_1e4 | 0.04232662 | 0.07184400 | 0.51524676 | False |
| regularized_3e5 | 0.03394117 | 0.05935059 | 0.44811704 | False |
| regularized_1e5 | 0.03141819 | 0.05429763 | 0.42129931 | False |
| regularized_1e6 | 0.04411295 | 0.07603320 | 0.51808069 | False |
| unregularized | 0.04178949 | 0.07269428 | 0.51484656 | False |
| unregularized_perturbed | 0.02794748 | 0.04715493 | 0.36329644 | False |
| frozen_weak_control | 0.01322685 | 0.01865455 | 0.20509031 | False |
| frozen_strong_control | 0.14325604 | 0.16771537 | 0.37381286 | False |

## Resources and limits

- Sidecar elapsed since first inspection: 1206.0 seconds; fitting orchestration: 784.6 seconds.
- Four CPU cores and an 8 GiB address-space cap enforced for each fit; maximum worker wall time 403.41 seconds; maximum peak RSS 989.43 MiB.
- All eight new fits reached the predeclared optimization time cap; stopping was checked between objective evaluations, with a separate 430-second worker timeout. These are budget-limited results, not converged-optimum certificates.
- The original weak warm-start fitting cost is not included in incremental per-fit times; see RESOURCE_REPORT.json.

## Interpretation

Weaker regularization did not produce a passing public-data point fit in this bounded portfolio. This does not establish that the frozen gates are unattainable: all new fits were time-limited, and no conclusions are drawn about the separate full-posterior control or any fresh champion.

## Frozen hashes

- `PREREGISTRATION.json`: `2f03df5acd8333103249b8507903c4574daa9be2d4960bc6288816ca2f7e0801`
- `OUTPUTS_FROZEN.json`: `bfd9071b0c7cd2998b1f04583e5f348862496122c64c65fa99838c87d2761f33`
- `queries.json`: `761383ac96567f501cefb9d5d759850f4ea3948604db0f58b5c31a8c6891cdd5`
- `best_predictions.npz`: `c5ad34208e89fe22589e22a71f9eb5dec4fa5ddeee87bf28bb0d9ca5adc28e14`
- `best_parameters.npz`: `63072c839b2462434423a5bd424a4a06cf0b709b2d0beeb3b5bb8939d60f4ea6`
- `RESULTS.json`: `63ade60ce56b84270a8c3d02a6a075018d43dad0db5472ff50397b136b807aab`

- Frozen at 2026-08-28T21:56:52.428202+00:00; first scoring began at 2026-08-28T21:56:53.844337+00:00.
- Cached exact-label SHA-256: `a53ff964558b620ddde624d89e6f57e27db95073bf5223439f1ede7f765fb6e1`.
- All frozen source, parameter, and prediction hashes remain unchanged.
