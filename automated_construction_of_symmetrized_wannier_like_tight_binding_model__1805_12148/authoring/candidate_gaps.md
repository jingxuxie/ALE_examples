# Solution-gap ledger

This is an author-only discovery ledger, not participant instructions. Selection is empirical: no concept is rejected solely because a generic solver might work. References are pinned in `sources/`; later code, regression outputs, and evaluation cases must never be mounted into a participant run.

## A — Historical geometric covariance failures
- Starting artifact: TBmodels before the cell-remapping rounding fix and before order-configurable folding, with its older geometry implementation and actual InAs models.
- Private solution: TBmodels PR #100 (`eb5393c`, 2021-03-31), PR #101 (`e1034c3`, 2021-04-06), folding implementation `120d7d1`, and official regression data.
- Outcome: transformations, folding, and symmetry reduction produce the same physical Hamiltonian in a specified orbital gauge.
- Shortcut: compare sorted eigenvalues or round every fractional coordinate independently.
- Failure regime: non-orthogonal cells, orbitals on boundaries, nontrivial orbital order, and changes of origin; equal spectra do not determine the requested gauge.
- Independent bottlenecks: integer-lattice remapping; orbital correspondence; conjugate-pair accounting and Bloch phases.
- Check: stored matrix-valued reference results, spectra, covariance and inverse-operation checks.

## B — Localized-gauge symmetry beyond fixed atomic orbitals
- Starting artifact: the original fixed atomic-orbital workflow, which explicitly omits maximal localization; Hamiltonians and gauge/overlap information are available but localized-gauge operators are not.
- Private solution: later symmetry-adapted Wannier implementations (WannierBerri/SAWF and WannSymm); exact module and fixtures require the adjacent-source feasibility audit.
- Outcome: physically covariant symmetrized models in a nontrivial Wannier gauge, not just restored band degeneracy.
- Shortcut: average constant representation matrices over the point group.
- Failure regime: momentum-dependent sewing, nonsymmorphic phases, antiunitary operations, and transformed position operators.
- Independent bottlenecks: gauge transport; affine operator transformation; real-space support closure.
- Check: official reference tensors, covariance identities, and Berry/position observables.

## C — Realistic device-scale reduction
- Starting artifact: bulk Wannier models and original direct dense evaluation, without later efficient cell handling or reduced-subspace machinery.
- Private solution: TBmodels later supercell implementation (`a613d8e`, `00abbfb`), large-model Hamiltonian fix (`2120b85`), and official Kwant 1.5.0 stabilized modes/scattering. Pymablock was an adjacent research lead, not the built oracle.
- Outcome: low-energy device observables or reduced models at a scale where dense device diagonalization is not viable.
- Shortcut: expand every dense hopping block and diagonalize each device at every parameter.
- Failure regime: many thousands of orbitals, long-range hoppings, many parameter values, near-degenerate target manifolds.
- Independent bottlenecks: sparse geometry assembly; subspace isolation; effective-operator or transport evaluation.
- Check: precomputed sparse-reference outputs, resource measurement, and bulk/device consistency.

## D — Transfer from III–V atomic sp bases
- Starting artifact: fixed sp/sp3 orbital representation utilities used for Si and III–V examples.
- Private solution: later WannierBerri/WannSymm orbital and magnetic-symmetry implementations; the built pilot verifies the WannierBerri Fe d-orbital branch. Unverified symmetry-representation issue workarounds are not treated as qualified strong solutions.
- Outcome: valid representations and symmetrized operator families for different orbital/physical families.
- Shortcut: signed orbital permutations and a single spin rotation recipe.
- Failure regime: real d harmonics, improper rotations, inequivalent local frames, antiunitary magnetic operations.
- Independent bottlenecks: angular-momentum conventions; site permutations/translations; spinor and antiunitary composition.
- Check: representation composition, stored author tensors, and full symmetry covariance.

## E — Band agreement is not magnetic-response agreement
- Starting artifact: a full-space tight-binding Taylor model, raw ab-initio momentum/spin matrices, and symmetry matrices in an unknown degenerate basis; no target-band reduction or standard-gauge fitting.
- Private solution: VASP2KP, arXiv:2312.08729, official `zjwang11/VASP2KP` implementation and the verified Bi2Se3, MoSe2, MoTe2 and WTe2 matrix exports. Additional materials discussed in the paper are not assumed to have downloadable matrix data.
- Outcome: standard-basis low-energy Hamiltonian and Zeeman tensors, including remote-band effects.
- Shortcut: project the Hamiltonian directly or infer parameters only from eigenvalues.
- Failure regime: quasi-degenerate manifolds, orbital Zeeman contributions, complex intertwiners, and cubic corrections.
- Independent bottlenecks: unitary/antiunitary gauge identification; high-order quasi-degenerate downfolding; magnetic effective operators.
- Check: privileged source-generated coefficients, matrix-valued responses, covariance, and weak-field spectra.

## F — Import-to-symmetry integration
- Starting artifact: historical parsers and symmetrization with the original Cartesian/reduced-coordinate, nearest-atom and order-greater-than-two faults.
- Private solution: TBmodels fixes `bc20bcb`, `84cdd38`, `1c2c102`, official Si/Bi Wannier90 files including wsvec, and nonsymmorphic Si example.
- Outcome: correct interpolation after parsing, centre assignment and symmetry projection.
- Shortcut: ignore wsvec, use fractional Euclidean distance, and apply each generator once.
- Failure regime: Wigner–Seitz degeneracy corrections, skew cells, noncommuting generators and nonsymmorphic translations.
- Independent bottlenecks: input semantic recovery; metric-aware centre mapping; group closure and real-space transformation.
- Check: stored full Hamiltonians in both conventions, symmetry residues, and real reference datasets.

## G — A missing target-subspace ablation
- Starting artifact: the original energy-window fit score and optimized models, without independently checking orbital character, effective masses or magnetic response.
- Private solution sought: the paper's expensive author calculation/provenance export and independently computed response tables; later automated-projection workflows where usable. This original-window ablation route was not qualified: the supplement/archive limits and mocked optimizer tests are documented in `workflow_research.md`. It is a candidate audit direction, not a claim that an ablation defect in the paper was established.
- Outcome: distinguish a superficially good band fit from a physically correct low-energy model and repair the actual mismatch.
- Shortcut: minimize only sorted band RMS or tune a global energy shift.
- Failure regime: band inversion, character exchanges, strained L-valley discrepancy, and target-band crossings.
- Independent bottlenecks: target tracking; constrained selection; independent response validation.
- Check: withheld author data and physical response metrics, not the optimization surrogate itself.

## H — Correctness versus operator interpolation cost
- Starting artifact: Hamiltonian-only interpolation, which omits off-diagonal position/dipole matrix elements (TBmodels issue #173) and may use dense many-k tensors.
- Private solution: later WannierBerri real-space operator and response interpolation, official stored regression data, and TBmodels performance fix `2120b85`.
- Outcome: response functions with full position/gauge contributions without a prohibitive all-k dense intermediate.
- Shortcut: differentiate band energies or Hamiltonians alone; apply a fixed dense Fourier/eigensolver kernel.
- Failure regime: nonzero external position contributions, near degeneracies, non-Abelian subspaces and dense k meshes.
- Independent bottlenecks: operator semantics; degenerate response construction; memory-bounded interpolation/integration.
- Check: official response references, component ablations, runtime and peak memory.

## Initial anti-compression decisions

The potential compound pilots are A+F (historical covariance pipeline), B+D (localized/magnetic operator symmetry), C+H (device/response scale), and E+G (gauge-resolved effective physics). Final feasibility and implementation choices are recorded before each build. A single universal numerical kernel is not sufficient: each proposed pilot has multiple separately scored physical modules. This claim still needs adversarial empirical testing, not acceptance on assertion.

## Primary source locations
- https://arxiv.org/abs/1805.12148 and included appendices/supplement links
- https://github.com/Z2PackDev/TBmodels (complete history locally cloned)
- https://github.com/Z2PackDev/TBmodels/pull/100
- https://github.com/Z2PackDev/TBmodels/pull/101
- https://github.com/Z2PackDev/TBmodels/issues/114
- https://github.com/Z2PackDev/TBmodels/issues/173
- https://github.com/Z2PackDev/symmetry-representation
- https://github.com/ccao/WannSymm
- https://github.com/wannier-berri/wannier-berri
- https://github.com/zjwang11/VASP2KP
- https://arxiv.org/abs/2312.08729
- https://arxiv.org/abs/2404.03728
- https://pymablock.readthedocs.io/en/latest/

Feasibility caveat: a public claim or an open issue is not itself a private solution. Every built pilot must identify an executable later implementation or stored authoritative outputs. If not found, that route is recorded as unbuilt or explicitly synthetic, not silently promoted to a source-grounded gap.

## Final qualification

Four pilots were built: historical import/cell covariance (A+F), magnetic position-operator and response integration (B+D+H), real long-range device transport (C+F+H), and standard-gauge effective Hamiltonian/Zeeman reduction (E, with G motivating independent response checks). This does not claim that the original energy-window ablation or full symmetry-adapted localization workflow was built. The latter remained an unbuilt research lead; no fifth pilot was constructed.

All four have executable privileged references. None survives the frontier-hard acceptance gate: three are robustly solved; the remaining operator residual rests on an unspecified repair convention. See the valid tournament, counterexample audits, and `FINAL_REPORT.md` for the empirical rejection rather than inferring hardness from the gap ledger.
