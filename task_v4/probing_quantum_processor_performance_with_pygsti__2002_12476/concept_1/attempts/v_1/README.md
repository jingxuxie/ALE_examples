# Robust processor-characterization submission

`design.json` is the required submission: exactly one `batches` field containing 840 nonnegative integers.

## Feasibility

- Execution cost: 1,599,872 / 1,600,000 ticks.
- Distinct circuits: 24 / 24.
- Total batches: 650; independent shots: 41,600.
- Maximum batches per circuit: 48 / 48.

## Validation

| Dataset | Overall A-risk reduction | Worst-regime reduction |
| --- | ---: | ---: |
| Supplied development points | 63.6097% | 55.6863% |
| Independent final validation, 24,000 points | 64.5154% | 61.4620% |

Final validation uses 4,000 fresh points from each disclosed regime, with seed 91380746, after selecting the design. Both required thresholds, 50% overall and 40% in every regime, are exceeded on both datasets. These are local Fisher-information A-risk reductions, not finite-sample estimator guarantees or private-evaluator results.

`public_check.json` contains the supplied checker's result. `validation_summary.json` contains feasibility, per-regime results, paired-bootstrap intervals, and model-consistency checks.

## Method

The allocation minimizes scaled core-parameter A-risk using the full 14-parameter information inverse, retaining correlations with both unknown readout parameters. Optimization combines operating-regime sampling, continuous allocation, circuit-support exchanges, and cost-aware integer rounding. Additional idle-rotation stress points identify long-circuit sensitivity gaps. The final selection favors robust regime margins over a marginally larger mean-only score.

Optimization sources, logs, intermediate allocations, and final validation risks are retained under `work/`. Large intermediate Fisher-feature caches were removed.
