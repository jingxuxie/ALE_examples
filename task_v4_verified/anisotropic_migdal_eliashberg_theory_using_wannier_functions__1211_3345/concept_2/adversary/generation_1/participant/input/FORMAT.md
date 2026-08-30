# Input, equations, and output

All energies are in meV and temperatures in kelvin. There are eight equally weighted Fermi-surface patches and three positive Einstein phonon energies. These are effective, reciprocal, nonnegative electron–phonon spectral kernels; positive-semidefiniteness of the patch matrices is not required.

## Fixed input

`reference.npz` contains float64 arrays:

| Key | Shape | Meaning |
|---|---|---|
| `reference` | `(3,8,8)` | A feasible kernel, mode first |
| `weights` | `(8,)` | Positive DOS weights, sum one |
| `energies_mev` | `(3,)` | Nominal phonon energies |
| `row_sums` | `(3,8)` | `reference @ weights` |
| `diagonal` | `(3,8)` | Mode diagonals |
| `static` | `(8,8)` | Sum of the three mode matrices |

The constraint arrays, not an inferred degree histogram or sorted profile, define the instance. Each submitted kernel must match them individually. `config.json` fixes all numerical conventions. Comparisons have zero relative tolerance. Symmetrization by `(C + C.T)/2` removes only accepted roundoff; it is not a feasibility repair. Raw and symmetrized arrays must pass the invariant checks.

## Spectral and normal-state equations

For mode matrices `C[s,i,j]`, define

    alpha2F_ij(Omega) = (1/2) sum_s Omega_s C_sij delta(Omega - Omega_s)
    Lambda_ij(nu) = sum_s C_sij Omega_s^2 / (Omega_s^2 + nu^2)
    r_si = sum_j weights_j C_sij
    R_i(nu) = sum_s r_si Omega_s^2 / (Omega_s^2 + nu^2)
    lambda_i = sum_s r_si

Consequently the isotropic spectrum is `(1/2) sum_s Omega_s (sum_i weights_i r_si) delta(Omega-Omega_s)`. Matching all `r_si` gives identical normal-state `Z` at every temperature and Matsubara frequency. Matching `sum_s C_s` additionally fixes the complete static interaction, not merely its largest eigenvalue.

For positive Matsubara indices `n = 0,...,M-1`, set `thermal = k_B T` and `omega_n = (2n+1) pi thermal`. The infinite normal-state Matsubara sum has the exact finite expression

    Z_i(n) = 1 + [R_i(0) + 2 sum_(ell=1)^n R_i(2 pi thermal ell)] / (2n+1).

In particular, `Z_i(0) = 1 + lambda_i`. Do not truncate the normal-state sum at the pairing cutoff.

## Linearized transition

The even-frequency, zero-Coulomb gap equation is

    Z_i(n) Delta_i(n) = pi thermal sum_(j,m>=0) weights_j
        [Lambda_ij(omega_n-omega_m) + Lambda_ij(omega_n+omega_m)]
        Delta_j(m) / omega_m.

For the finite pairing cutoff `M`, use the real symmetric matrix

    H_(i,n),(j,m) = pi thermal sqrt(weights_i weights_j)
        [Lambda_ij(omega_n-omega_m) + Lambda_ij(omega_n+omega_m)]
        / sqrt(omega_n Z_i(n) omega_m Z_j(m)).

Its largest algebraic eigenvalue crosses one at the transition. `physics.py` brackets and solves this root, with residual checks. All supplied instances use the configured temperature bracket. This numerical benchmark uses these finite operators plus explicit refinement checks; it does not claim an interval-certified infinite-cutoff transition.

Each spectral family multiplies the three supplied energies by its fixed factors, identically for both kernels. The equality constraints remain unchanged. Compute both transitions at `M=96,192` for every family and at `M=384` for the nominal family. Choose the high/low kernel ordering from nominal `M=192` and retain that ordering everywhere. The score is the minimum of all these ratios. Every successive refinement must satisfy the configured relative drift limit. Equality at the target threshold succeeds; there is no score rounding grace.

The evaluator additionally assembles a signed-frequency operator independently and runs a regular-row no-go control. At zero Coulomb repulsion, frequency-resolved row regularity implies an isotropic leading positive eigenvector, so rewiring regular kernels must not change their transition.

## Fixed spectral scenarios

The nominal mode energies are `(4,25,100)` meV. Keep the three mode matrices and their labels unchanged while applying each scenario to both submitted kernels:

| Scenario | Mode energies (meV) |
|---|---|
| `nominal` | `(4,25,100)` |
| `compressed_spectrum` | `(4.2,25,95)` |
| `expanded_spectrum` | `(3.8,25,105)` |
| `independent_branch_0` | `(4,100,45)` |

The last scenario independently shifts two branches and reverses their frequency ordering. Do not sort the frequencies without applying the same permutation to all mode-resolved data. The matrices parameterize integrated mode couplings, not fixed delta-function spectral weights: the prefactor `Omega_s C_sij / 2` changes with the scenario. Every scenario separately has matched isotropic spectra and matched normal-state functions between the two kernels.

These are alternative effective positive-phonon models used for a worst-case stress test, not a realistic isotope range or a continuous material deformation. No matrix invariant or bound depends on the chosen scenario. The required minimum ratio is `1.09` over nine evaluations: two grids for each of four scenarios, plus the nominal `M=384` grid. The full static aggregate remains fixed even when branch energies cross. `core_score` and `worst_family_score` both denote this minimum; evaluator resource measurements exclude candidate search because no candidate code is executed.

## Artifact

Write exactly one array:

    np.savez_compressed(output_path, kernels=np.stack([kernel_a, kernel_b]))

The shape is exactly `(2,3,8,8)`. Real integer or floating dtypes up to eight bytes per element are accepted; complex, object, boolean, nonfinite, malformed, oversized, and extra-key archives are rejected. Prefer float64. The file must be a regular single-link file, not a symlink or hardlink; symlink path components are also rejected. Compressed size, declared ZIP expansion, and NPY headers are checked before loading any array. Evaluation consumes only this artifact; it does not import or execute submitted code. Pass an explicit output filename to avoid accidentally writing `witness.npz.npz`.

## Background

The Fermi-surface-restricted equations and spectral normalization follow Margine and Giustino, arXiv:1211.3345, Eqs. (18)–(23), (39). The normal-state telescoping expression and multiband linearization are also discussed by Dolgov and Golubov, arXiv:0803.1103. The supplied benchmark equations are authoritative if notation differs. A wide-band model with electronic scales well above the phonon energies is assumed; phonon stability and a material-specific microscopic realization are not inferred from these arrays.
