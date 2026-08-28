# Portable coefficient service

From any directory:

```sh
bash OUTPUT/run.sh --requests REQUESTS.json --output PREDICTIONS.json --profile production
```

`CONVENTIONS.md` is the scientific contract. `release.json` is the supplied public
campaign, copied without modification. Only Python 3, NumPy and mpmath are needed
by the service; SciPy is also used by independent tests. No CAS or network is used.
The launchers set numerical-library thread counts to one.

`loopaudit/massive.py` performs dimensionless parameter integration, causal
simplex deformation, analytic Laurent/Taylor expansion, and directional adaptive
subdivision. `loopaudit/infrared.py` evaluates the supported massless topologies
analytically. `service.py` assembles epsilon polynomials before truncating.
There is no result cache, routing sort, epsilon fit, finite-difference Taylor
stencil, Gram inverse, or physical-width regulator in the repaired service.

## Diagnostics

All requested coefficients have `uv`, `ir2`, `ir1`, `finite` complex pairs, using
the starter's coefficient/order schema. Integral-level `seconds`, `work`,
`estimated_error`, `strategy`, and `converged` apply to the jointly computed local
coefficients; the table repeats these diagnostics for each requested order.
`work` counts parameter-node evaluations, including rejected refinement levels;
an analytic IR coefficient costs one work unit. These units are not FLOPs.
`estimated_error` is a **relative**, maximum Laurent-vector quadrature discrepancy
over the requested orders, or a floating-point floor for analytic formulas.
The adaptive estimate sums cell discrepancies. It is not a rigorous bound.
`converged=false` and `UNCONVERGED` mean refinement limits were exhausted: the
returned nonzero estimate is diagnostic, not a certified prediction. No failure
is converted to zero. Unsupported massless topologies raise explicit errors.

Observable diagnostics include measured assembly time and operation count;
their error estimates are propagated and divided by the observable normalization.
That normalization never changes any coefficient. The service does not use
`expected_zero` to alter results.

## Executable controls and reproduction

- `production`: moderate Gaussian levels, causal strength 3, directional adaptive
  fallback; relative stopping target `3e-11`.
- `fixed`: deliberately insufficient low-order ablation, no subdivision.
- `direct`: strength 2, stricter target, higher-order independent refinement.
- `tensor_only`: remove subdivision from production's order sequence.
- `adaptive_cyclic`: same limits as production, but cycle split directions.
- `order_8` through `order_80`: fixed-resolution work/accuracy studies. These
  intentionally do not claim convergence (`relative_tolerance=0`).

All numeric settings are in `profiles.json`. These profiles change algorithms or
actual work, not only labels. The `direct` profile is a comparison calculation,
not an external exact oracle; exact checks are separately reported.
The output-root `configuration_manifest.json` maps every table profile label to
its launcher and settings, including the `inherited_*` labels, which use the
separate, unchanged `baseline/run.sh` executable.

```sh
bash OUTPUT/reproduce.sh
python3 OUTPUT/workspace/check_claims.py
```

The first command reruns the public profiles, scientific tests, baseline
comparison, and synthetic stress ablations, regenerating all published tables
and figure CSVs. `--skip-stress` skips only the extra stress campaign. The
baseline measured outputs remain fixed; to remeasure the unmodified baseline:

```sh
cd OUTPUT
python3 baseline/workspace/experiments.py --submission baseline --requests workspace/release.json
python3 baseline/workspace/diagnose.py baseline/runs/production.json
```

`workspace/stress_requests.json` contains independently chosen threshold,
hierarchical-mass, and high-weight requests; the production engine has no
request-ID dispatch. Exploratory `stress.py` and `extra_stress.py` reproduce the
broader stress sweeps from the output root. `baseline/` preserves the old source,
settings, launcher, failed calibration log, prediction JSON, and diagnosis.
