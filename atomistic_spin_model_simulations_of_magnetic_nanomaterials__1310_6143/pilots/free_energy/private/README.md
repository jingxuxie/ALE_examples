# Constrained thermal free-energy pilot

The participant must recover finite-temperature magnetization-direction torque
and free-energy curves for three competing-anisotropy families with 2,048 or
2,744 spins. This is an equilibrium sampling and thermodynamic-integration task,
not a local-energy kernel benchmark. No model agents were launched in authoring.

## Handoff

- Expose only `participant/` and an initially empty `attempt/` to the participant.
- `participant/TASK.md` is the short task; `participant/input/FORMAT.md` specifies
  the entire physical, numerical, execution, and scoring contract.
- The participant gets local energy/torque and ordinary unconstrained Metropolis
  helpers plus an explicitly uncontrolled coherent-rotation baseline. It gets
  neither constrained moves nor stored answers.
- `private/weak_submission/solve.py` is the baseline entry point. `attempt/` is
  deliberately empty, including hidden files.
- `private/strong_submission/` is a runnable, privileged official-CMC solution,
  not a gold-result lookup. Never mount it in a participant session.
- Six initial, twelve challenge, and six confirmation cases are hash-frozen in
  `private/challenge_pool/manifest.json`. Unused seeds and parameter/size regions
  are recorded separately in `private/challenge_pool/ratchet_reserve.json`.

## Evaluation

From this pilot root, with the supplied Python runtime available:

```
python private/evaluator.py --submission attempt --output private/attempt_scores.json --split initial
python private/evaluator.py --submission private/weak_submission --output private/baseline_cli_initial.json --split initial
python private/evaluator.py --submission private/strong_submission --output private/strong_cli_initial.json --split initial
```

The common trusted `../../authoring/isolated.py` supplies bubblewrap isolation.
The evaluator must execute outside the parent sandbox's network-namespace
restriction; it does not fall back to unsandboxed execution. Submission code is
never imported. Reference, other pilots, authoring sources, home, and networking
are not mounted. Filesystem paths supplied to the solver remain absolute.
The participant runtime belongs in `participant/workspace/vendor`; main may
replace that vendor directory. It is excluded from the pilot content seal.

The 600-second per-case limit accommodates the independent two-chain C++ strong
solution on one CPU. This is intentionally longer than the common harness's
default 180 seconds. Compilation is permitted only in writable scratch space.
Runtime is reported separately from continuously decreasing accuracy scores.

## Audit artifacts

- `private/baseline_scores.json`: all-split trusted baseline calibration.
- `private/strong_reference_scores.json`: independent-seed, independently
  integrated strong calibration, including per-case errors and native timing.
- `private/baseline_cli_initial.json`: actual isolated baseline CLI smoke test.
- `private/reference/results/`: stored torque/free-energy means and standard
  errors; `raw/` retains every blocked trajectory and its seed/runtime.
- `private/reference/validation.json`: chain convergence, direction/norm drift,
  endpoint/reflection tests, and initial sparse/dense angular checks.
- `private/reference/validation_before_extension.json`: retained original
  convergence outliers; none are silently removed.
- `private/reference/independent_checks.json`: independent Python/C++ energies,
  local/global energy differences, rigid-rotation torque finite differences,
  dimensionless Boltzmann scaling, and original-source hash checks.
- `private/reference/angular_refinement.json`: 9 versus 17 angular nodes with
  covariance-aware refinement uncertainties; final gold uses 17 nodes.
- `private/BUILD_STATUS.json` and `private/provenance.json`: readiness gates and
  content hashes, generated last by `private/reference/seal.py`.

## Independent bottlenecks

1. Preserve the correct directional solid-angle measure and constrained
   detailed balance, while allowing magnetization length to fluctuate.
2. Equilibrate collective modes and competing surface/interface/bulk terms;
   cold and high-temperature starts need not relax at the same rate.
3. Recover a multi-harmonic torque curve and integrate its sign and normalization
   accurately; a single-angle or single-sine estimate is insufficient.

## Scientific limits

These are explicitly specified finite classical model magnets, not fitted
material predictions. There are no quantum corrections, dipolar interactions,
or thermodynamic-limit extrapolations. The reference constrains total moment
direction, not separate layer directions. Native setup uses equal moments,
one numerical material, a standard C++ RNG, and a dimensionless-energy shim;
the official constrained acceptance and proposal functions are unchanged.

Stored standard errors include blocked within-chain and between-chain noise;
they are not rigorous confidence guarantees against undiscovered metastability.
The angular-refinement difference and its uncertainty are reported separately,
not mislabeled as sampling SEM. Seven sine modes on 17 nodes remain a controlled
numerical approximation, not an exact representation of the continuous curve.
Strong calibration uses separate trajectories but the same official transition
kernel; it is not claimed to be an independently invented CMC implementation.
Exact symmetries and independent energy/torque derivatives provide checks beyond
same-kernel comparisons. Offline calibration timing is not claimed to be an
end-to-end isolated strong-solver timing.

Reproduction commands and primary-source locations are in
`private/reference/README.md`.
