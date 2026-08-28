# Validation record

These are public-input and analytic checks, not comparisons with unavailable
private references. No reference predictions are embedded in the solver.

## Analytic and independent checks

- Projected heat-bath/overrelaxation, projected Wolff clusters, and the separate
  explicit-Jacobian pair sampler agree with deterministic two-spin quadrature.
  The test includes unequal onsite tensors, cubic anisotropy, axial two-ion
  anisotropy, and three nonsymmetry angles.
- The isotropic two-spin directional ensemble gives mean magnetization per
  spin `2/3`, rather than constraining its magnitude. Its torque vanishes.
- Native torque agrees with finite energy differences for 100 configurations
  with all off-diagonal tensor components present. The saved rotation-energy
  coefficients reproduce the native torque to roundoff.
- Symmetry-folded MBAR agrees with analytic Gaussian partition functions.
  Its torque is the negative derivative of its free energy, and the reflection
  and periodicity identities hold. Adding arbitrary reduced-energy offsets
  spanning 800 units leaves the inferred distributions unchanged.
- Large-system pair and projected-kernel estimates agree within their batch
  errors in the higher-temperature exchange-spring case.
- Python syntax checks and C++17 `-Wall -Wextra -Wpedantic` checks pass.

## Supplied cases

All six supplied inputs were run with a development budget of 140 seconds
(about 125 seconds of actual elapsed time each). All produce finite,
correctly sized arrays, zero torque at both symmetry endpoints, and exactly
zero free energy at the origin. All use the multistate free-energy estimator.
One low-temperature reweighting initialization issue was identified, corrected
by energy recentering and a stable fixed-point warm start, and covered by the
energy-offset regression test. Its saved configurations were reprocessed and
the corrected entry point was also rerun.

The surface cases predict opposite signs of `f(pi/2)-f(0)` at their two
temperatures, illustrating that this implementation does not merely rescale
the coherent-rotation landscape. This is a solver prediction, not an external
accuracy validation.

## Full-budget execution

An independent-seed run of `initial_interface_spring_01` (seed 876053) used the default
550-second budget under a 4-GiB address-space limit:

- Wall time, including compilation and startup: **535.85 seconds**.
- Total reported user plus system CPU time: **546.24 seconds**.
- Peak resident memory: **181,612 KiB**, approximately **177 MiB**.
- Exit status: zero; all output-contract assertions pass.
- Saved configurations: 76,892; no sampling files are retained by a normal run.

Compared with the shorter run using the original seed, the maximum torque
difference is `2.10e-5` per spin, or 1.20 combined estimated standard errors.
The maximum free-energy difference is `5.71e-6` per spin, or 0.54 combined
standard errors. The full-run interior torque standard errors range from
`4.25e-6` to `9.63e-6` per spin.

The runtime has substantial headroom below the 600-wall-second and
602-CPU-second limits. These measurements do not guarantee identical timing
on other hardware or establish convergence in more strongly metastable cases.
See `README.md` for the sampling derivation and scientific limitations.
