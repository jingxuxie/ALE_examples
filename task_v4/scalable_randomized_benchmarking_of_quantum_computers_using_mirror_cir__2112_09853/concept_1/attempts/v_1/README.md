# Calibration-matched counterexample

The submission is `witness.json`. Validate it from this directory with:

```sh
python ../../participant/workspace/check.py witness.json
```

The supplied checker accepts the witness:

| Quantity | Result | Requirement |
| --- | ---: | ---: |
| Relative fitted-infidelity bias | 0.024522934492178 | at least 0.0244 |
| Maximum polarization fit residual | 0.003912427154108 | at most 0.004 |
| Depth-256 polarization | 0.006551281377193 | at least 0.005 |
| Fitted infidelity | 0.019509541310156 | true infidelity is 0.02 |
| Inverse-pair integer overlap | 32640 | exactly 32640 |

Every noise row sums to 60, every integer lies within its specified bounds,
and the weighted global-Pauli marginals match the baseline exactly. The
depth-two polarization is 0.9603357281045753. Only the noise allocation changes;
the ensemble, stationary noise semantics, and fitting procedure remain fixed.

## Reproduction

The included search uses the installed NumPy, SciPy, and NetworkX packages,
without network access. Run:

```sh
python optimize.py 0 1500
python round_search.py continuous_0.npy 1
python ../../participant/workspace/check.py witness.json
```

`optimize.py` differentiates the exact Pauli-transfer recurrence and fitted
decay, then optimizes a continuous allocation subject to the linear calibration
constraints, quadratic overlap equality, and count bounds. Its analytic
gradient is checked against a directional finite difference.

`round_search.py` uses integer minimum-cost flow to preserve all row sums and
weighted marginals during rounding. Integer cycle moves then restore the exact
overlap. It calls the supplied constraint checker and full evaluator before
reporting acceptance. `validation.json` records a separate public-checker run.

This is a counterexample to the supplied quantitative robustness claim, not a
critique of the paper's general theorem.
