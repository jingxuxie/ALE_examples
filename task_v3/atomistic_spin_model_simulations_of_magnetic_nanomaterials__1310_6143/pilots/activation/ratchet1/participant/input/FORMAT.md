# Physical and execution contract (version 1)

## Hamiltonian

There are N classical, three-component, unit-length magnetic moments with open
boundaries, indexed 0 through N-1. All energies are in meV. The input specifies

`E(s) = -sum_{i=0}^{N-2} J[i] dot(s[i],s[i+1])
        -sum_i dot(s[i], A[i] @ s[i]) -sum_i dot(h,s[i])`.

`exchange_meV` contains N-1 positive nearest-neighbor exchanges.
`anisotropy_meV` contains N symmetric 3x3 tensors: a positive eigenvalue is an
easy-axis coefficient; a negative one is a hard-axis coefficient. Each bond is
counted once (there is no additional 1/2). `field_meV` is the common Zeeman
energy vector h = mu_s * mu_B * B, not a field in tesla. `mu_s_muB` is the
moment in Bohr magnetons. No DMI, dipoles, periodic bond, or pinned spins is
implicit. Site order is physical chain order. `temperature_K` is descriptive;
the requested harmonic factor is temperature independent for these cases.

`minimum_a` and `minimum_b` are N x 3 relaxed configurations. A is metastable;
report the forward barrier E(saddle)-E(A), not the reverse barrier or energy per
spin. The target is the lowest connecting index-one stationary state found for
these two basins. Physically equivalent symmetry-related saddles are accepted
through invariant energies and spectra, not coordinate matching. Distinct
higher saddles do not receive full barrier credit. The private reference is a
validated numerical transition, not a proof of a global mountain-pass minimum.

## Tangent spectrum and harmonic factor

For any block-orthonormal tangent basis T (two columns per spin, orthogonal to
s), the constrained Hessian is

`H_T = T.T @ (H_E - blockdiag((s[i] dot grad_i E) I_3)) @ T`.

Here H_E is the Euclidean Cartesian Hessian. Its complete 2N eigenvalues,
in meV per radian squared, are basis invariant. At A they must all be positive;
at the saddle precisely one must be negative. These cases deliberately break
continuous spin-rotation symmetry with hard-axis anisotropy and a transverse
field. No zero-mode removal, absolute-value replacement of unstable modes,
or arbitrary eigenvalue clipping is part of the requested answer.

The required natural logarithm of the dimensionless harmonic HTST factor is

`log_omega0 = 0.5 * [sum_all log(lambda_A / E0)
                         - sum_positive log(lambda_saddle / E0)]`,

where E0 = 1 meV. This is the fluctuation/entropy component Omega_0, not the
full dynamical spin-precession attempt frequency and not an Arrhenius rate.
The negative saddle eigenvalue is excluded from this determinant ratio but
must be included in the reported spectrum. Full magnetic dynamical prefactors
and zero-mode-volume calculations are outside this pilot's contract.

## Invocation and files

Run `python solve.py CASE.json OUTPUT.npz`. An output containing a JSON object
is also accepted, including at the requested `.npz` pathname. The grader runs
one fresh subprocess per case. Use only supplied input, submitted files, and
installed numerical packages. The supplied `energy.py` is available beside
`solve.py` in the grading process. Do not assume a working directory outside
the submission sandbox. No external network or private library access is
permitted. NumPy/SciPy are available; Numba is optional, not guaranteed.

Required NPZ keys (no object arrays/pickles), or JSON fields:

| Key | Shape | Meaning |
|---|---|---|
| `saddle` | N x 3 | unit spin vectors, norm error <= 1e-5 |
| `barrier_meV` | scalar | E(saddle)-E(A), total meV |
| `eigenvalues_min_meV` | 2N | ascending complete tangent spectrum at A |
| `eigenvalues_saddle_meV` | 2N | ascending complete tangent saddle spectrum |
| `log_omega0` | scalar | natural logarithm defined above |

All values must be finite. Output and uncompressed archive contents must each
be <=2 MB, submission <=32 MiB excluding generated Python/Numba caches,
memory <=2 GiB, and wall time <=90 seconds per case. CPU libraries are limited
to one thread. Output, temporary files, and logs must fit the 128 MiB per-file
limit. Cases span short coherent chains and long boundary-nucleation or
soft-interface chains, with N up to 4,096. Hidden cases use separately chosen
parameters and lengths, not the exact demonstration instances. No hidden
answers, saddle seeds, or previous diagnostic results are supplied.

`workspace/baseline.py` is a complete short-chain solver, supplied as a starting
point rather than a performance guarantee. Run it with the same two positional
arguments as the required submission. You may copy and modify it. The physical
model, output fields, and numerical scoring scales are unchanged from its
short-chain contract; the extension concerns spatially localized mechanisms,
long-chain basin connectivity, and scalable fluctuation calculations. No exact
finite-difference or dense-Hessian implementation is required.

## Continuous scoring

The evaluator independently recomputes energy, tangent gradient, Hessian,
eigenvalues, and inertia from submitted spins. All physical penalties are
continuous, including changes of saddle index; there is no index gate or
clipped normalized score. Define the following losses:

- Barrier: the sum of absolute reported-vs-reference and
  reported-vs-recomputed errors divided by `0.03 B+0.005` and `0.02 B+0.002`
  meV, respectively, where B is the native-validated reference barrier.
- Stationarity: `asinh(r/2e-5)`, with r the maximum spinwise tangent-gradient
  norm in meV. This fixed physical tolerance is not tightened between rounds.
- Spectrum: the mean of the two RMS differences in `asinh(lambda/0.001 meV)`
  between reported and independently recomputed spectra, divided by 0.12.
  The signed transform continuously penalizes sign and soft-mode errors.
- Prefactor: `abs(reported_log_omega0-reference_log_omega0)/0.25`.
- Inertia: `softplus(lambda_s[0]/0.02 meV) +
  sum_{j>=1} softplus(-lambda_s[j]/0.02 meV)`, where
  `softplus(x)=log(1+exp(x))`. This penalizes a missing unstable direction,
  extra unstable modes, and near-zero modes without discontinuous rejection.
  The 0.02 meV scale is about 5% of the easy-axis energy, not an accuracy ratchet.

Search loss is inertia + 0.25 barrier + 0.20 stationarity. Fluctuation loss is
0.30 spectrum + 0.25 prefactor. Divide each by the corresponding loss of the
ordinary-relaxation weak anchor, giving a and b, and define
`L=((a**4+b**4)/2)**0.25`. This continuously penalizes missing either independent
capability rather than averaging it away. Let W and S be balanced losses of the weak
anchor and the independently checked native strong reference. Runtime adds
`D=0.001*log(1+t/max(0.25,t_ref))`, where t_ref is the measured native source
runtime. Gain is `g=(W-L-D)/(W-S)` and case score is
`1-exp(-log(2)*exp(log(4)*g))`.

This baseline-relative exponential is not clipped: with runtime omitted,
the weak anchor scores 0.5, the strong anchor 0.9375, worse results can score
below 0.5, and improvements beyond the strong anchor continue toward 1.
No finite-quality plateau is imposed. Malformed output or timeout scores zero.
Each family is averaged equally; final score is 0.7 times the mean family
score plus 0.3 times the worst family score. Both transition search and
fluctuation calculation are required for a high score.
