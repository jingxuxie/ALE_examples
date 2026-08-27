# Finite-volume spectrum campaign: repair and controlled extension

## Diagnosis and revision

The initial executable was run unchanged; its tables are retained in
`baseline/`. Three issues have different observable signatures. Equating
infinite-line and circle normal ordering loses both the vacuum constant and
lower-degree interactions; a common scalar shift cannot repair excitation
gaps. Omitted Fock states induce more than a vacuum counterterm, and their
effect depends on the energy of the external state. Finally, an all-ones
Krylov starting vector preserves reflection even when the archive contains
both reflection sectors. This can miss a low reflection-odd state rather than
merely perturb its eigenvalue. A random, fixed-seed start removes that
unintended restriction. Tiny dense matrices are diagonalized directly.

The revised pipeline was rerun at four cutoffs for all five branches. Operator
assembly was separately checked against the retired oscillator implementation
after explicitly projecting onto its reflection-even basis. That comparison
agreed at floating-point roundoff. The live calculation uses the unquotiented
archives and retains multiplicities.

## Retained method and alternatives

The physical couplings are first converted with the finite-circle contraction
difference. Image sums include the alternating sign for twisted boundary
conditions; the corresponding massive Casimir energy sets the absolute energy
convention. Cubic vertices induce a linear term under this conversion. Fourier
components are retained and convolved, rather than replacing a modulated
profile by its spatial average.

The Gaussian branch is solved analytically after the exact mass change. It is
an independent control, not a fitted label. For interacting cases, short-time
Wick contractions give high-energy spectral densities. The leading integrated
tail is a sum of local normal-ordered operators. A second calculation includes
external-state-energy dependence as a first-order expectation value after the
local Hamiltonian is diagonalized. The asymptotic density is not extrapolated
through its unphysical infrared singularity: the shifted integration starts
above five reference masses. A 241-point interpolation resolves the resulting
smooth state-energy dependence. This threshold is a modeling control, not a
physical new cutoff.

`ablation.csv` contains bare truncation with the correct physical energy
convention and local-only elimination, alongside the production calculation
in `results.csv`. These are distinct physics approximations, not repetitions
with different names. Applying the full nonlocal correction as an exact
Hamiltonian rather than perturbatively was not retained: high-basis-energy
matrix elements lie outside the asymptotic approximation's safe domain.

## Evidence and scope

The tables and plots show vacuum and gap cutoff trajectories, not alleged
exact answers. `claims.json` computes explicit adjacent-cutoff drift ratios
per branch. Some adjacent-cutoff comparisons can deteriorate because the
sharp finite-volume shell structure is irregular; a lower drift is not by
itself an accuracy certificate. The local/nonlocal ablation diagnoses the
substantial state dependence of the excited levels, particularly on the
twisted circle. Source and modulation effects are retained rather than treated
as mere relabelings of a homogeneous parity block.

Independent higher-cutoff runs, a Gaussian exact check, and local-versus-
state-dependent comparisons underpin the numerical reference. Residual
higher-order and derivative corrections remain. Neither a finite-volume gap
nor an explicitly biased model determines an infinite-volume critical
coupling; this campaign supports a bounded finite-volume convergence claim,
not a new phase-transition estimate.

`scaling.csv` records actual wall time, archive dimension, and the process
high-water resident memory. No additional Fock states are generated for the
interacting production replay. The Gaussian analytic control enumerates a
small free spectrum only to order the exact levels. The entry point is
self-contained, single-BLAS-threaded, and independent of the working directory.
