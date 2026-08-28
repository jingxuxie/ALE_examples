# Rescued finite-volume scalar-spectrum campaign

## Executive assessment

The inherited scalar correction does **not** repair excitation energies. It is
an identity operator and therefore cancels identically from gaps. The starter
also omits the finite-circle change of normal ordering and the free Casimir
energy. In the short, modulated circle these are substantial physical effects,
not ultraviolet errors. Finally, its all-ones Lanczos start can exclude
reflection-odd eigenvectors; the archive has not quotiented that symmetry.

The replacement uses the exact Gaussian solution where applicable. For the
interacting branches it independently generates a larger Fock basis, adds
finite-volume, second-order Wick-contraction tails, and extrapolates the
remaining cutoff dependence over many actual energy shells. It does not fit
any supplied spectrum, identify parameters by archive name, or import supplied
states above the requested cutoff.

The interacting estimates are approximate, not certified bounds on the
untruncated theory. Their internal higher-cutoff check changes the requested
absolute energies by at most 0.00074, 0.00122, 0.00106 and 0.00213 in the
periodic, twisted, biased and modulated branches respectively. These checks
share a tail approximation and cannot establish absolute accuracy by
themselves. The independent Gaussian calibration is reproduced to roundoff.

## Reproduction and deliverables

```
bash /path/to/this/output/run.sh /path/to/request.json /path/to/new_results
```

The entry point works from an arbitrary working directory, compiles its two
small C++ programs in the destination, uses one BLAS/OpenMP thread, resolves
`archive_root` relative to the request, and never writes to an input archive.
Python, NumPy, SciPy, Pillow, and a C++17 compiler are its only dependencies.

- `baseline/` contains the **initial**, unmodified campaign; `baseline_code/`
  preserves its executable implementation.
- `results.csv` contains production energies, common-vacuum gaps, and the
  physical vacuum itself in `vacuum_energy`.
- `ablation.csv` contains physically normalized `raw`, `local_tail`,
  `generated_raw`, and `generated_local` configurations. The last two apply
  only to interacting branches.
- `scaling.csv`, `runtime.json`, and `diagnostics.json` expose the extra basis,
  actual measured costs, every extrapolation sample, and sensitivity estimates.
- The primary figure plots the lowest positive gap; the robustness figure
  plots the absolute vacuum. Every point is linked to a spectrum row by
  `figures/source.csv`. These are not independent data sets.
- `experiments/` preserves convergence tables, revision results, a larger-basis
  study, a momentum-window stress test, and a trimmed/renamed replay.

## 1. Correct Hamiltonian and energy convention

Let `s=+1` for periodic and `s=-1` for antiperiodic boundary conditions. The
finite contraction difference and free vacuum energy used here are

```
d = (1/pi) sum_{j>=1} s^j K0(j m L)
Ecas(m,L) = -(m/pi) sum_{j>=1} s^j K1(j m L)/j.
```

Image sums are exponentially converged. Wick conversion is applied separately
to **each Fourier coefficient**, without introducing a factorial into a
coupling:

```
:phi^n:_infinity,m = sum_a n! d^a / [2^a a! (n-2a)!]
                           :phi^(n-2a):_circle,m.
```

Thus quartic interactions induce `6 d g4` in the quadratic coefficient and
`3 d^2 g4` in the scalar coefficient. Cubic interactions induce `3 d g3` in
the linear coefficient. Only the zero-transfer scalar integrates to a
constant. `Ecas` is added, not subtracted. Twisting changes both image signs
and allowed oscillator momenta; it is not a periodic calculation with its
zero mode deleted after the fact.

For a homogeneous quadratic interaction, `M^2=m^2+2g2` and the exact vacuum is

```
E_vac = Ecas(M,L) + L/(8 pi) [M^2-m^2-M^2 log(M^2/m^2)].
```

Excitations are sums of frequencies `sqrt(M^2+(pi r/L)^2)` with exactly the
requested total momentum and number parity. Small independently generated
occupation lists enumerate the first three values, including multiplicities.
At the supplied calibration, the results are
`E_vac=-0.005822191596577917` and gap `1.0954451150103321`, versus the supplied
`-0.005822191596577913` and `1.0954451150103321`. This is a formula check, not
a parameter adjustment. The production quadratic case has the different
coupling 0.65 and is evaluated by the same formula.

## 2. Basis and numerical treatment

`generate.cpp` starts from the oscillator algebra, not the archived occupation
lists. A recursive enumeration retains states by **total free energy** and the
declared sector. Normal-ordered monomials are applied as ordered creation and
annihilation multisets, with Bose ladder factors and coefficient
`L n! / (product creation factorials product annihilation factorials)` times
the field normalization factors. Sparse duplicates are summed.

Generated degree-1 through degree-4 operators, including nonzero transfers,
were compared with the supplied projection after matching occupations. The
largest observed difference was `2.85e-14`. No reflection quotient is imposed.
The mixed sector includes both occupation parities; paired Fourier transfers,
not individual transfer operators, produce the Hermitian Hamiltonian.

Dense `eigh` is used for small matrices, and seeded, unconstrained random-start
ARPACK for larger ones. Hermiticity and eigenvector residuals are checked;
residuals above `2e-7` fail the calculation. Eigenvalues are not deduplicated.
Tests explicitly cover a reflection-odd ground state orthogonal to the
all-ones vector and a free unprojected doublet.

The interacting working cutoff initially is `34 m` (or the largest requested
cutoff if larger), reduced in steps of `m` until each sector has at most
45,000 generated states. It never drops below the largest requested cutoff.
The public interacting cases all use working cutoff 34. Their total generated
dimensions are 61,896, 15,191, 7,587, and 12,659. The Gaussian enumeration uses
16 states in total and frequencies of mass **M**, not mass m; its reported
generated cutoff is in that transformed Gaussian basis.

For momentum-unprojected cases only, there is an additional **approximate**
window `|P_doubled| <= max(8,4 max|q_input|)`. All blocks inside this window
are coupled; momentum is not treated as conserved. This controls the
large-circle modulated cost. In an independently generated stress case with
`L=5.5`, quartic mean 2, quartic Fourier amplitudes 0.7, quadratic Fourier
amplitudes 0.12, and energy cutoff 24, widening the window from 8 to the full
unprojected space changes any of the six requested raw levels by at most
`1.25e-5`. Window 12 differs by less than `7e-8`. This is an empirical control,
not a universal bound for arbitrarily strong or high-frequency modulation.

## 3. Eliminating omitted states

The starting identity is the Schur complement,

```
Delta H(E) = - V_LH (H_HH-E)^(-1) V_HL.
```

Full high-block diagonalization, a scalar-only counterterm, continuum-only
counterterms, and energy-dependent local approximations were considered.
The retained approximation uses `H0` in the high block and the local part of
the short-distance product of two interaction vertices. For degrees `n,p`
with `k` cross-contracted lines, its combinatorial factor is

```
binom(n,k) binom(p,k) k!,       2 <= k <= min(n,p).
```

It multiplies `V[n+p-2k,q+q']` and `-g_tilde[n,q] g_tilde[p,q'] I[k,Q](B)`.
Both orders of distinct vertices are included. Consequently the correction
contains quadratic and quartic operators as well as the identity; cubic and
linear corrections appear in the biased branch. Profile products generate
the additional transfer harmonics required in the modulated branch. A
linear vertex alone has no leading hard multi-line loop; its nonperturbative
low-energy effects are included by the expanded mixed basis.

Unlike a plane-only asymptotic counterterm, the spectral weight is computed
from actual finite-circle oscillator momenta:

```
rho[k,Q](E) = L/(2L)^k sum_{r1+...+rk=Q}
                 delta(E-omega1-...-omegak)/(omega1...omegak)
I[k,Q](B) = integral_B^infinity rho[k,Q](E) dE/E.
```

Unordered tuples carry their exact multiplicities. Enumeration extends to
total loop energy `160 m`. For nonuniform profiles, the local center-coordinate
approximation uses `Q=(q-q')/2`, interpolated between compatible momentum
lattices. In particular, an odd number of antiperiodic lines uses the lowest
compatible nonzero momentum, not a nonexistent zero-momentum triple.
External-momentum/derivative dependence beyond this approximation is omitted.

Above the loop enumeration limit the analytic short-distance densities are

```
rho2 = 1/(2 pi E^2)
rho3 = 3 log(E/m)/(4 pi^2 E^2)
rho4 = [3 log(E/m)^2/(4 pi^3) - 1/(16 pi)]/E^2.
```

Finite-image additions are `3 d rho2` for rho3 and
`4 d rho3 + 6 d^2 rho2` for rho4. A convergent quadrature integrates the
remaining infinite tail. Spectral tuple counts are reported separately from
the diagonalized basis dimensions. A unit test checks the complete quartic
vacuum shell between energies 10 and 20 against explicit matrix-element
elimination, for both boundaries, to 11 decimal places. This verifies the
normalization and combinatorics independently of the extrapolation.

The remaining local approximation error includes interacting high-block
effects, external energies, and derivative terms. To reduce it without
claiming that second order is exact, the code diagonalizes 17 actual shell
cutoffs from `Bmax-8m` to `Bmax` in steps of `0.5m`. Each level is fitted to
`a+b(Bmax/B)^3`, with least-squares row multiplier `(B/Bmax)^3`. The intercept
is the production estimate. The power reflects the next inverse-energy
denominator; logarithms and higher orders make it a working asymptotic ansatz,
not a theorem. Varying the power to 2.5 and 3.5, or dropping the lowest four
samples, supplies sensitivity estimates. The `uncertainty` column is their
maximum with a 0.0005 floor, **not** a statistical confidence interval or a
guaranteed error bar. Gap errors also involve uncertainty in the common
vacuum and are correlated across levels.

## 4. Run–diagnose–revise history

1. **Initial run:** copied and executed the inherited campaign before editing.
   Its production/scalar-twice shifts move all absolute levels by the same
   amount. They cannot change a gap, even when a vacuum plot appears flatter.
2. **Convention repair and independent construction:** derived the image
   correction, checked the Gaussian formula, and matched generated operators
   to the archives. `raw` now means genuinely uncorrected truncation of the
   **correct physical Hamiltonian**, not omission of physical circle terms.
3. **Tail experiment:** `experiments/convergence32/` compares raw, local-tail,
   and spectator-energy-dependent tails through generated cutoff 32. The
   latter was not retained. For example, the modulated even first excitation
   moves from 1.9888102 to 1.9811399 between 28 and 32 under that variant,
   versus 1.9875552 to 1.9879875 with the local tail. A more elaborate
   denominator is not automatically a more reliable finite-volume estimate.
4. **Ritz shortcut rejected:** `experiments/refinement.json` records an early
   12-vector reduced-space implementation. Direct midpoint checks found
   differences up to `8.4e-4`, relevant to the intended precision. Final
   production uses direct eigensolves at every sampled shell instead.
5. **Larger independently generated checks:** raw and local results through
   cutoff 40 are in `experiments/convergence40/`; a separate cutoff-38
   extrapolation is in `experiments/reference38/`. Its nine samples use unit
   spacing, also testing shell-sampling sensitivity. It is a convergence
   check, not an exact physical reference.
6. **Replay check:** physically trimmed every supplied archive to cutoff 12,
   renamed all archive directories, selected cutoffs 10 and 12, and ran from
   `workspace/tests/`. All 246 compared energy/gap rows agree with the full
   archive run to the recorded tolerance in
   `experiments/replay_validation.json`.

## 5. Results and claims that survive

The lowest positive excitation uses the odd sector except in the mixed case,
where it is level 1. Values below are rounded; CSV files retain full precision.

| Branch | Physical raw vacuum, C=10 to 16 | Physical raw gap, C=10 to 16 | Production vacuum | Production gap |
|---|---:|---:|---:|---:|
| Quadratic | -0.096338 to -0.097686 | 1.518415 to 1.516987 | -0.098594 | 1.516575 |
| Periodic quartic | -0.141564 to -0.202822 | 0.786500 to 0.730479 | -0.286361 | 0.686390 |
| Antiperiodic quartic | -0.128512 to -0.197438 | 1.065450 to 1.009180 | -0.288361 | 0.963886 |
| Biased | -0.234809 to -0.296115 | 0.966811 to 0.945334 | -0.371282 | 0.928158 |
| Modulated | -0.087227 to -0.108689 | 0.869745 to 0.824280 | -0.142386 | 0.799297 |

The starter's modulated gap at C=16 was 0.743636: its proximity to any stable
curve would not make it the right finite-volume observable. The physical
normal-ordering repair changes that raw gap to 0.824280 before any ultraviolet
tail is added. The source-broken case is treated as one mixed space throughout.
The closely spaced modulated odd levels remain separate; no degeneracy is
removed by rounding or uniqueness filtering.

The main improvement claim is supported by three distinct observations:
(i) an independent exact Gaussian check, (ii) exact oscillator and finite-shell
identities, and (iii) stability under a larger newly generated working basis.
All four interacting branches show much smaller residual changes in the
larger-basis comparison than the physical raw C=10-to-16 drifts. The modulated
branch has the largest remaining ambiguity, about 0.0021 in that comparison.
Higher twisted excitation energies have sensitivity estimates as large as
0.0038. Sub-millith precision is not established for every level.

**Important qualification about `claims.json`:** the ten required row-linked
vacuum/gap drift ratios are zero. Production's independently generated working
basis is held fixed while the requested archive cutoff changes; Gaussian
results are analytic. Thus these ratios are zero **by construction**, and are
not evidence that a cutoff-10 archive alone resolves the spectrum. The
`generated_raw` ablation is equally flat in requested cutoff while retaining a
substantial omitted-state bias. Its presence is a direct counterexample to
equating flatness with physical accuracy. Expanded-basis cost and generated
shell convergence, rather than these ratios, are the relevant comparison.

## 6. Cost, validation, and limitations

The first full repaired public replay took approximately 38 seconds and
404 MiB process high-water RSS, with compilation in addition. The final exact
measurements are in `runtime.json`. The larger cutoff-38 development check
took 78.5 seconds and 936 MiB. These are actual measured runs, not estimates
from sparse array sizes. Memory is the maximum parent/child **process**
high-water mark, not a sum of simultaneous process memories and not a
case-local allocation measurement. The allocator/process high-water mark can
remain high for later small cases.

Generation, spectral enumeration, counting probes, and all 17 shell solves
are included in each case's measured shared setup. The setup is reused across
requested cutoffs and the generated-basis ablations. `elapsed_s` and
`shared_setup_s` repeat this measured cost on those rows and **must not be
summed**; `incremental_s` identifies the separate archive-truncation solves.
`dimension` sums the actual diagonalized sector dimensions; only one large
sector is assembled at a time. `retained_dimension` separately records the
dimension available in the supplied projection. Extra generated work is not
hidden under the smaller requested cutoff label.

Seven tests pass: archive algebra, Wick/image conventions, exact Gaussian
calibration, a Gaussian variational bound, explicit finite-shell elimination,
reflection-odd solver access, and free multiplicity. Run them from the output
root with `PYTHONPATH=workspace python3 -m unittest discover -s workspace/tests
-v`; set `TASK_REQUEST` to a request file to include the optional archive test.
The archived test log used the supplied campaign. `validate_artifacts.py`
checks unique IDs, common-vacuum arithmetic, all quantitative claims, and
every figure source coordinate. Trimmed replay verifies that the extra
physics is independently generated rather than borrowed from a larger input.

Remaining limitations are the local high-energy expansion, its momentum
interpolation, the finite loop-sum matching, the momentum window for
inhomogeneous cases, and the chosen asymptotic regression. Neither the local
tail nor its extrapolation preserves a variational upper bound. The public
quartic checks are not independent exact solutions, and a common systematic
tail error could survive them. Very strong modulation, very small reference
mass, or parameters far outside the documented range require renewed window,
working-cutoff, and asymptotic-sensitivity tests. No claim of a universal
renormalization prescription or a certified untruncated answer is made.
