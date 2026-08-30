# Executable model contract

## Physical scope and normalization

The normalized Fermi-surface measure is `dtheta/(2*pi)`, with `v(theta) = (cos(theta), sin(theta))`. Units absorb the common density-of-states, charge, velocity magnitude, and thermal prefactors. The equilibrium phonon bath is fixed. This is an angular, quasielastic reduction: it does not claim exact finite-energy emission/absorption kinematics or an independently realizable crystal.

The nonnegative angular **scattering-power kernel**, rather than an unsquared quantum amplitude, is Fourier limited. A positive kernel can be interpreted as a squared coupling in this reduction; its square root need not be Fourier limited. Frequency and angle are separable: mode `nu` has scattering-power kernel `w_nu*K`, with frequencies and positive weights given in `model.json`. The weights sum to one and already include the fixed operating-point factors. No temperature extrapolation is part of this task.

## Artifact and basis

Submit a UTF-8 JSON object with exactly these keys:

```
{"schema_version": 1, "kernel_a": [[...], ...], "kernel_b": [[...], ...]}
```

Each matrix is 18×18. Rows/columns are ordered
`sqrt(2)*cos(theta), sqrt(2)*sin(theta), sqrt(2)*cos(2*theta), sqrt(2)*sin(2*theta), ..., sqrt(2)*sin(9*theta)`.
Write this column vector as `phi(theta)`. For either submitted coefficient matrix `C`,

```
K(theta, theta_prime) = 1 + phi(theta)^T C phi(theta_prime).
```

Entries must be finite JSON numbers, not strings or booleans, with magnitude at most one. Duplicate JSON keys, nonstandard NaN/Infinity constants, extra keys, and nonregular/symlink witness files are rejected.

## Admissibility

For each matrix, to coefficient tolerance `1e-10`:

- `C = C^T` (reciprocity).
- Entries coupling harmonics of opposite parity are zero (simultaneous inversion of both angles).
- The leading 2×2 coefficient block is zero.

The degree profile is consequently `d(theta) = integral K(theta,theta_prime) dtheta_prime/(2*pi) = 1` at every angle. Define

```
D_ab = (1/2) integral integral K(theta,theta_prime)
       * [v_a(theta)-v_a(theta_prime)]
       * [v_b(theta)-v_b(theta_prime)] dtheta dtheta_prime/(2*pi)^2.
```

Both kernels must have the full matrix `D = I_2/2`, not just its trace. The linewidth spectral moments are `sum_nu w_nu*omega_nu^r * d(theta)`, and the transport spectral moments are `sum_nu w_nu*omega_nu^r * D`. The evaluator independently checks `r = 0, 1, 2`, all row degrees, and the full matrices on all refinement grids. This separable model actually matches these observables frequency by frequency.

Uniform continuum bounds are `0.08 <= K <= 6.0`. They prohibit zero edges, disconnected components, and arbitrarily large dynamic range (the maximum ratio is 75). These bounds imply a collision-operator gap of at least 0.08 on mean-zero functions; the evaluator also checks that gap independently in the Fourier representation.

### Required continuum certificate

Let `m_a` be the harmonic frequency of basis component `a`. On the unshifted 1024×1024 uniform torus grid, let `K_min` and `K_max` be the extrema, `h = 2*pi/1024`, and

```
E = (h*h/4) * sum_ab abs(C_ab) * (m_a*m_a + m_b*m_b).
```

The witness must satisfy `K_min-E >= 0.08` and `K_max+E <= 6.0`, up to coefficient tolerance. This is a sufficient continuum certificate, not merely a sampled positivity test: sequential one-dimensional linear-interpolation error bounds give this enclosure using the uniform second-derivative bounds. A genuinely admissible kernel too close to a bound can fail this conservative certificate; satisfying the certificate is explicitly part of the contract.

## Conductivity and verification

The method under test retains only the degree profile and velocity-projected Dirichlet matrix, and therefore assigns the same transport prediction to both kernels. Its benchmark sufficiency claim is that this data loss cannot hide a conductivity-trace ratio of 1.75 or larger. The checker falsifies that claim by reproducing the exact collision-equation responses. This claim is introduced for this benchmark, not quoted from EPW.

For each driving direction solve the mean-zero equation

```
(L f)(theta) = integral K(theta,theta_prime)
              * [f(theta)-f(theta_prime)] dtheta_prime/(2*pi)
L f_b = v_b
Sigma_ab = integral v_a(theta)*f_b(theta) dtheta/(2*pi).
```

In this finite-rank, constant-degree model the continuum conductivity is exactly the leading 2×2 block of `(I-C)^(-1) / 2`. The evaluator additionally constructs the collision matrix directly from sampled kernel values on 64, 128, and 256 angles, fixes the constant null mode, solves both drives, and checks the residual, zero mean, reciprocity, inversion, row degrees, pairwise Dirichlet sums, spectral moments, and conductivity against the Fourier result. All these grids exceed twice the Fourier bandwidth; exact Fourier quadrature explains why agreement is expected, rather than serving as an empirical continuum extrapolation.

Define `R = max(trace(Sigma_a),trace(Sigma_b))/min(trace(Sigma_a),trace(Sigma_b))`. The target is **R >= 1.75**, both analytically and on every refinement grid, with numerical discrepancy at most `1e-8`. The trace objective is rotation invariant, so merely relabeling or rotating an anisotropic conductivity cannot create a witness.

For valid artifacts, the core score is `max(0,(R-1)/0.75)` without clipping. Invalid artifacts score zero. Passing additionally requires the target and every check. No optimizer, reference witness, EPW executable, or candidate-supplied result is trusted by the evaluator.

## Local commands

```
python3 baseline/search.py --output /absolute/output/directory
python3 baseline/search.py --output /absolute/output/directory --trials 200 --seed 11
python3 workspace/model.py /absolute/output/directory/witness.json
```
