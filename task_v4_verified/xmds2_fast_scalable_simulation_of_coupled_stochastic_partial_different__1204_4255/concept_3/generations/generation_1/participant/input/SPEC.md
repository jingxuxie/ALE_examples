# Public protocol: coherent_gp_splitter_v1

This specification and `protocol.json` fix the target before any fresh-agent
tournament. Private cases only choose parameter values inside this specification.
They do not change the equations, target rule, time horizon, or control interface.
The task is a design/witness construction problem, not solver implementation.

## 1. Field equation and units

Set hbar = mass = nominal axial trap frequency = 1. The two-dimensional fields
`psi_a(x,y,t), psi_b(x,y,t)` live on `[-10,10) x [-6,6)` with periodic boundaries.
Total squared L2 norm is one. Let `rho_a = |psi_a|^2`, and similarly for b.

```text
i d_t psi_a = [-1/2 Laplacian + V_a + g rho_a + g r rho_b] psi_a
              + eta (Omega_x - i Omega_y) psi_b / 2
i d_t psi_b = [-1/2 Laplacian + V_b + g s rho_b + g r rho_a] psi_b
              + eta (Omega_x + i Omega_y) psi_a / 2

V_a = [w_x^2 kappa (x-c+d)^2 + (1.6 w_y)^2 y^2]/2
      + [Delta + b + z x]/2
V_b = [w_x^2 kappa (x-c-d)^2 + (1.6 w_y)^2 y^2]/2
      - [Delta + b + z x]/2
```

Control names are `center=c`, `separation=d`, `omega_x=Omega_x`,
`omega_y=Omega_y`, `detuning=Delta`, `curvature=kappa`. Duration is exactly `T=8`.
`kappa` multiplies axial frequency **squared**, not frequency. RF gain `eta`
multiplies both transverse quadratures, not `Delta`. No stochastic noise is
sampled during a trajectory: the uncertainty is static, adversarial calibration
and sample variation. The simulation is a genuine two-spatial-dimensional GP
model, not a two-level or Gaussian variational approximation.

The uncertain parameters form the full closed Cartesian product:

| JSON name | Symbol | Range |
| --- | --- | --- |
| g | g | [3,6] |
| self_ratio | s | [0.92,1.08] |
| cross_ratio | r | [0.8,1.15] |
| trap_x | w_x | [0.94,1.06] |
| trap_y | w_y | [0.97,1.03] |
| rf_gain | eta | [0.92,1.08] |
| bias | b | [-0.12,0.12] |
| gradient | z | [-0.035,0.035] |

All combinations, including corners, are allowed. No correlations may be assumed.
Nominal values are in `protocol.json`. A control cannot depend on these parameters.

## 2. Preparation and fixed target

Initially the controls are `(c,d,Omega_x,Omega_y,Delta,kappa)=(0,0,0,0,0,1)`.
For each case, prepare the positive, real scalar GP ground state `phi_in` with
mass one in component a and zero in component b, including that case's trap,
interaction and static differential potential. This is a reproducible physical
preparation, not a hidden input-state puzzle.

At T the controls must be `(1,2.2,0,0,0,1)`. The output trap centers are -1.2
and 3.2, up to the known rule for the uncertain static gradient. Let
`phi_a, phi_b` be the positive real minimum-energy coupled stationary profiles
for the final potentials with **each component norm squared fixed to 1/2**.
They minimize

```text
E = integral [ (|grad phi_a|^2 + |grad phi_b|^2)/2
    + V_a phi_a^2 + V_b phi_b^2
    + g phi_a^4/2 + g s phi_b^4/2 + g r phi_a^2 phi_b^2 ] dx dy.
```

The target is exactly `(phi_a, -i phi_b)`. Its phase is defined relative to the
same drive-frame axes for every case. Only one common global phase is irrelevant.
Targets account for physical uncertainty in stationary shape, but not arbitrary
case-dependent relative phases. This is an instantaneous coherent output at T,
not a promise of indefinitely phase-locked storage after the drive turns off.

For a normalized final state, coherent fidelity is
`F = |integral (phi_a psi_a + i phi_b psi_b) dx dy|^2`.
Density-only fidelity, separate phase alignment of the ports, and renormalizing
a bad propagated state are forbidden. A pure occupied output port can score at
most 1/2 against this balanced coherent target.

## 3. Artifact interface and hardware admissibility

Submit UTF-8 JSON, at most 65536 bytes, with exactly these top-level keys:

```json
{"schema_version":1,"controls":{"center":[],"separation":[],"omega_x":[],"omega_y":[],"detuning":[],"curvature":[]}}
```

Each array must contain exactly 25 finite JSON numbers. Use `baseline/control.json`
as a complete example. Booleans, strings, NaN/Infinity, duplicate keys, extra
keys, missing keys, wrong lengths, links/devices, and executable content are
rejected. No files other than the artifact are interpreted as a submission.

Let `K = [0,0,0,0, 8/22,2*8/22,...,21*8/22, 8,8,8,8]`.
The channel is the degree-three clamped B-spline on K whose 25 coefficients are
the submitted values. This is C2, not an interpolation through 25 time samples.
The first three coefficients equal the channel start value, and the last three
equal its end value: endpoint first and second derivatives vanish. Tests allow
absolute floating-point tolerance `1e-12` on these algebraic constraints.

| Channel | All coefficient bounds | Slew certificate | Acceleration certificate | Start -> end |
| --- | --- | --- | --- | --- |
| center | [-0.5,1.8] | 1.2 | 6 | 0 -> 1 |
| separation | [-0.4,2.7] | 1.8 | 8 | 0 -> 2.2 |
| omega_x | [-2.8,2.8] | 5 | 24 | 0 -> 0 |
| omega_y | [-2.8,2.8] | 5 | 24 | 0 -> 0 |
| detuning | [-3,3] | 6 | 30 | 0 -> 0 |
| curvature | [0.75,1.3] | 0.7 | 4 | 1 -> 1 |

For every coefficient index, `hypot(omega_x[index],omega_y[index]) <= 2.8`.
Derivative coefficients are obtained by the standard B-spline derivative rule:
`d_i = p (c_(i+1)-c_i)/(K_(i+p+1)-K_(i+1))`, with the end knot removed at each
derivative and degree decreased. **Every** first/second derivative coefficient
must obey its table bound. These conservative control-polygon certificates are
part of admissibility, not merely sampled checks. Convexity guarantees the
continuous-time amplitude, RF-radius, slew and acceleration limits everywhere.
No monotonicity restriction is imposed: rejoining, echo pulses and overshoots
within the bounds are allowed. There are 114 free interior coefficients.

## 4. Evaluation and score

There are five families with equal weight: public (the five supplied cases),
interaction (four hidden cases varying g,s,r only), calibration (four varying
eta,b,z only), trap (four varying w_x,w_y,z only), and joint (four varying all
eight parameters). Non-varying coordinates are nominal. Joint cases may be
corners or interior points. The exact private coordinates are withheld to test
robustness, not to conceal mathematical requirements. Finite-case passing is not
a proof of uniform fidelity over the uncountable envelope.

The trusted implementation uses complex128 Fourier tensor grids, exact kinetic
exponentials, exact local nonlinear phase flows, exact two-component RF rotations,
and a symmetric midpoint split step. It does not execute the submitted artifact
or import any participant code. Evaluation runs every case on:

1. A: 80x40, dt=0.010;
2. B: 112x56, dt=0.010;
3. C: 112x56, dt=0.005.

Stationary states are recomputed on each grid and checked for relative L2
stationary-equation residual <= 2e-6. Define
`e = 2*(|F_A-F_B|+|F_B-F_C|)+2e-6`, and `Q=max(0,F_C-e)`.
The factor two and fixed reference allowance are conservative empirical error
allowances, **not rigorous interval enclosures**. A candidate is uncertified if
any case has `e>2e-4`, global-phase-aligned L2 state disagreement above 0.002
between A/B (Fourier resampled) or B/C, norm error above 1e-10, boundary-region
mass above 1e-8, or high-frequency spectral mass above 1e-8. Boundary means
`|x|>=8 or |y|>=4.8`; spectral tail means either FFT frequency magnitude at least
0.4 cycles/sample. Norm/boundary/tail diagnostics are sampled every 20 steps
including first and final steps, on all three trajectories. Numerical audit
failure produces `valid=false`, zero official fidelity scores, and a reason.

Each family score is the mean of Q in that family. `core_score` is the equal-weight
mean of the five family scores; `worst_family_score` is their minimum;
`worst_case_score` is the minimum Q. A valid pass requires all three thresholds:
0.990, 0.985, 0.980, respectively. Ranking is lexicographic by core score,
worst-family score, worst-case score, then resource score; invalid artifacts
rank below all valid ones. Fixed thresholds do not move after seeing contestants.

`resource_score = 1 - mean_t [0.5 R + 0.25 M + 0.25 D]`, where
`R=(Omega_x^2+Omega_y^2)/2.8^2`,
`M=((c'/1.2)^2+(d'/1.8)^2)/2`, and `D=(Delta/3)^2`.
Five-point Gauss-Legendre quadrature on every knot span integrates these
polynomials exactly to floating precision. This is an actuator-use tie-breaker,
not a quantum speed-limit claim. `runtime_score=min(1,180/runtime_seconds)` is an
evaluator-cost diagnostic only, never a pass gate or ranking term. Construction
runtime cannot be inferred from a static artifact and is managed externally by
the tournament budget. Every score JSON includes finite core, worst-family,
runtime and resource scores, booleans `valid`/`passed`, and a reason.

## 5. Development API and cautions

`workspace/field_control.py` exposes `validate_artifact`, `references`, `evolve`,
`fidelities`, `case_arrays`, `summarize` and `resource_score`. See `workspace/smoke.py`
for a minimal caller. Add custom cases inside the public box; do not optimize
only the nominal case. References are cached by parameter/grid hash and are
independent of the waveform. The smoke script uses 64x32 and dt=0.04; it reports
uncertified diagnostic scores and always sets `passed=false`. It is not the
trusted scoring implementation. High score at that resolution is insufficient.

Any construction method is allowed within the tournament resources. Neither a
particular optimizer nor the original XMDS2 code generator is required. The
weak baseline uses an early near-pi/2 RF pulse and a spline approximation to
harmonic inverse-engineered transport `q_trap=q_desired+q_desired''`, with a
ninth-degree smooth-step desired trajectory delayed until t=2.2, after the RF
pulse. Spline projection may introduce small pre-2.2 motion. It neglects nonlinear redistribution,
RF/trap coupling and robust phase compensation. It is not optimized for fidelity.
