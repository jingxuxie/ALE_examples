# Adjacent research for arXiv:1805.12148

Audit: **2026-08-28 UTC / 2026-08-27 America/Los_Angeles**. Research and artifact inspection only: no pilot, solver implementation, package installation, or numerical reference run was performed. TBmodels history remains with the parent. The parent's VASP2KP gauge-identification/downfolding/Zeeman pilot is explicitly excluded from the recommendation.

## Decision for the parent

**Select diamond symmetry-compatible initial-projection search, upstream of SAWF construction.** Its core is bounded integer enumeration across little-group representation constraints, not Hamiltonian group averaging, eigendecomposition, or VASP2KP-style gauge identification. Official WannierBerri code, raw DFT wavefunctions, and tests with explicit expected answers all exist. The most defensible pre-solution artifact is `sources/wannier-berri/tests/data/diamond/di.save/`: **475,963 bytes** across eleven files. A builder can prepare representation-count tables once and expose a NumPy-only search task. This is an existing upstream workflow, not a proposed new research problem. [P1, P2, D1]

**Readiness qualification:** the files and numerical cache schema were inspected, but the reference was not executed. The remaining build gate is to reproduce the two upstream diamond projection-search assertions from the pinned source and freeze only their *inputs*. The 33,674-byte `diamond.sawf.npz` cache is useful for authoring, but includes Wannier-representation blocks and must not be passed through indiscriminately. [P2, D1, D2]

Five grounded opportunities follow. They are distinct bottlenecks, **not a claim that five new pilots have been built or that every candidate satisfies the parent's diversity criterion**. In particular, H+position symmetrization has a real physical distinction but remains computationally close to group averaging; MRWF is a reserve rather than another gauge pilot.

## Verified sources, releases, and local artifacts

The three official source clones are under this note's `sources/` directory:

| Local directory | Inspected commit | Scope |
|---|---|---|
| `wannier-berri/` | `e046ddc4bfe026ba1f9af2376f04babac5677425` | Projection search, SAWF, operator construction, real test data; commit dated 2026-08-14 |
| `WannierBerri-tutorial/` | `efe56e5b312a903bdbf06dcfc7b5fb8bb44c2afb` | Te H+position and Pt spin-Hall input/reference files; commit dated 2026-04-06 |
| `Wannier.jl/` | `ae4368abe60f7d6167c9e783e8aafca235038f10` | Parallel transport / manifold remixing and dataset manifest; commit dated 2026-04-10 |

These are inspected source snapshots, not assertions that their default branches equal published packages. [WB, TUT, JL]

Important later-release findings:

- **WannierBerri PyPI is 26.7.0, uploaded July 14, 2026.** GitHub's `/releases/latest` instead returns tag `v1.7.0`, published February 16, 2026. Do not use that GitHub endpoint or a documentation banner to infer the newest package. The tutorial's `tested_version = '1.3.0'` also coexists with much newer execution output. Pin source and data together. [WBPY, WBREL, T1]
- **Wannier90 v4.0.2 was published August 27, 2026, 12:29:41 UTC**, with automatic projectability-disentanglement thresholds. The preceding v4.0.1 includes projectability disentanglement, higher-order finite differences, a translationally invariant position-matrix formulation, and the Ryoo spin-Hall implementation. “PDWF is not released yet” is therefore an obsolete reading of the 2023 paper's code-availability statement. [W90REL, PD]
- **Wannier.jl's GitHub release is v0.3.6, November 15, 2025**, commit `75b619aba8057589779d3c11c69d089edcf235c3`. The inspected later source declares 0.4.0 and reorganizes localization modules. Use the pinned test files rather than assuming old tutorial identifiers still work. [JLREL, JL]
- The pinned WannierBerri `pyproject.toml` separates the modest base dependencies from symmetry, Ray, FFTW, plotting, and test extras. Full `[tests]` also pulls GPAW and unrelated model packages. **Do not install `[all]` or `[tests]` just to run the projection-search kernel.** [ENV]

Measured sizes below are local file sizes, not estimates from paper abstracts:

| Artifact | Size / contents | Status |
|---|---|---|
| Diamond `di.save/` | 475,963 B; eight `wfc*.dat`, XML, charge density, C pseudopotential | Cloned and inspected; upstream test's raw input |
| Diamond `diamond.sawf.npz` | 33,674 B; band blocks, `eig_irr`, space-group data, and Wannier blocks | Loaded with NumPy; three irreducible k points; curate before release |
| Diamond `.eig` + `.win` | 3,120 B + 938 B | Cloned; useful independent energy/structure provenance |
| Fe SAWF `Fe-444-sitesym/` input NPZs | `Fe.mmn.npz` 11,897,150 B; `.amn.npz` 509,226 B; `.eig.npz` 29,121 B; `.bkvec.npz` 60,436 B | Cloned; roughly 12 MB plus symmetry/checkpoint metadata |
| Trigonal Te `Te_tb.dat` | 17,305,196 B; 24 WFs, 195 real-space vectors, H and position blocks | Cloned; actual numerical data, not just VASP inputs |
| Pt `.mmn` + `.spn` + `.eig` | 11,920,055 B total | Cloned; compact pre-solution operator-reconstruction inputs |
| Pt with `.amn` + `.win` as well | 13,776,960 B total | Supports the older file-oriented conversion workflow |
| Pt `.sHu` and `.sIu` | 14,168,152 B each | Cloned; keep as evaluator/physics-comparison artifacts |
| `sources/Si2_coarse.tar.gz` | 37,780,816 B | Downloaded from the official Julia artifact manifest; SHA256 verified |

The main WannierBerri clone's full `tests/data` is about 162 MiB. None of these candidate tasks needs that whole directory. [D1, D3, TDATA, PTDATA, JDATA]

## 1. Selected: symmetry-compatible projection search for diamond

### Grounded gap and independent bottleneck

The 2018 workflow starts from a specified local orbital basis. A separate upstream problem is choosing initial orbitals and Wyckoff positions that can represent the bands in a requested energy window. WannierBerri's official projection-search tutorial formulates exactly this workflow; it does not promise that representation compatibility alone guarantees good localization. [BASE, P1]

For each irreducible k point and irrep, a projection combination must cover the frozen-window multiplicity without exceeding the outer-window multiplicity. There are also a total-WF budget, fixed projections, and per-projection multiplicity limits. The solver searches nonnegative integer combinations and filters them across k points. This is a combinatorial feasibility/completeness problem; the diagonalization and representation extraction belong to input preparation, not the proposed task's central computation. [P2]

### Concrete reference boundary

- `wannierberri/symmetry/projections_searcher.py`: `EBRsearcher.find_combinations` starts at line 193, `find_combinations_max` at 245, and `check_combinations_min_max` at 305 in the pinned snapshot.
- The two standalone kernels depend on NumPy, not Ray, a DFT executable, a Wannier minimizer, or an integer-programming service. The surrounding preparation path uses `SymmetrizerSAWF`, `Projection`/`ProjectionsSet`, and crystallographic representation tooling. [P2, P3]
- `tests/test_find_projections.py::test_find_projections_diamond` uses **six s-orbital trial positions**: `(0,0,0)`, `(x,0,0)`, `(1/2,1/2,1/2)`, `(1/4,1/4,1/4)`, `(1/8,1/8,1/8)`, `(0,x,z)`. It tests both inclusion and exclusion of time reversal. [P4]

### Best pre-solution artifact and leakage boundary

Use the actual QE bundle `tests/data/diamond/di.save/`, with the trial menu and energy-window definitions from the upstream test. It contains `data-file-schema.xml`, `wfc1.dat` through `wfc8.dat`, `charge-density.dat`, and `C.pz-vbc.UPF`; no new self-consistent calculation is needed to read those stored wavefunctions. The test calls `BandStructure.from_espresso(prefix=.../di, Ecut=100, include_TR=...)`, then constructs the band-side symmetrizer. [D1, P4]

For a bounded solver-facing task, the author can stop **before** `find_combinations` and export:

- trial-position/orbital labels and their WF dimensions;
- `irreps_per_projection_vectors` at each k point;
- `irreps_frozen_vectors`, `irreps_outer_vectors`;
- multiplicity caps, fixed flags, `num_wann_min/max`, and provenance for the energy windows.

Those are physical input features, not the selected projection coefficients. Keep answer vectors, `find_combinations` outputs, solution-bearing notebook cells, and the oracle source out of the learner-facing package. Do not synthesize random integer tables and call them diamond data. This packaging is a recommendation; it has **not** been performed. [P2, P4]

The existing `.sawf.npz` contains `eig_irr`, band symmetry blocks, and space-group metadata, but also `D_wann` information. It is a convenient authoring cache, not an automatically clean starting artifact. Either reconstruct from raw QE data, as the current projection test does, or retain only band-side information and independently generate the declared trial menu. [D2, P3, P4]

### Achievable oracle and limits

The existing test specifies two cases with `num_wann_max=10`: frozen `[-10,30]`, outer `[-20,50]`; and frozen `[-10,20]`, outer `[-20,25]`, in the data's energy units. **Evaluator-only** expected vectors are respectively `[0,0,0,1,0,0]` and `[1,0,0,0,0,0]`, each the only accepted combination. Reproduce these first; then compare complete result sets, integer feasibility, and dimensions rather than accepting one plausible-looking answer. [P4]

The current implementation explicitly accepts nonmagnetic type-I/type-II groups, rejects type-III/type-IV magnetic groups, and asserts against spinors. Do not enlarge this candidate into magnetic EBR classification. Matching the tested irrep constraints is also **not** a proof of topological triviality or successful MLWF construction. [P2]

**Recommendation:** highest priority. It has the smallest clean raw artifact, a sharply different algorithmic core, and exact existing reference assertions. The unexecuted preparation/reproduction check is its only immediate readiness gate.

## 2. Reserve: symmetry-adapted disentanglement with a frozen window in bcc Fe

**Gap.** Post-hoc averaging assumes a representation of the chosen orbitals. Constructing localized orbitals while preserving the desired representation and retaining frozen bands is a different optimization problem. Koretsune's 2023 follow-up explicitly treats frozen-window-compatible SAWF and irreducible-BZ input generation; its examples include Fe, Cu, Nb, and Co3Sn2S2. The paper says data are available on request, but later official WannierBerri tests supply actual compact Fe numerical inputs. [KOR, SYMW, S1]

**Reference and artifact.** Use `tests/data/Fe-444-sitesym/` and `tests/test_wannierise.py::test_sitesym_Fe`, not an invented model. The test loads `.amn/.eig/.mmn/.chk` NPZs and `Fe_TR={True,False}.sawf.npz`, and invokes `wannierise(..., sitesym=True, localise=True, num_iter=40, parallel=...)`. Its numerical core spans `wannierisation/wannierise.py` and the SAWF symmetry modules. Both reference source and input data are locally available. [D3, S1, S2]

**Pre-solution choice.** Expose the initial projections, overlaps, eigenvalues, k-mesh metadata, desired orbital representation, and declared frozen/outer windows. Exclude reference spreads and the reference band file. Inspect checkpoint contents and reset/omit any optimized gauge before defining it as an input: a file named `.chk` is not necessarily pre-solution. `Fe_bands_pw.dat` is an independent DFT comparison artifact, not a task input containing the answer. [S1, D3]

**Oracle.** The upstream Fe test checks centers at the origin to `1e-6`, symmetry-related spread equalities to `1e-8`, spread bounds, and stored spread references. The diamond SAWF test additionally supplies the explicit spread reference `0.39864755` with `1e-5` tolerance. Grade subspaces, frozen-band retention, and symmetry/center constraints, not elementwise agreement between nonunique gauges. The latter grading choice is a recommendation, not a reported run. [S1]

**Distinctness / feasibility.** This is iterative symmetry-constrained subspace/localization optimization in a ferromagnetic SOC family. It is not merely another material for a group-average task, but it still contains spectral steps and is substantially heavier than projection search. Use a serial bounded run; do not pull the whole GPAW/Ray test environment. SAWF symmetry of H also does not automatically make every finite-difference position/Berry matrix exactly symmetric. [ENV, SYMLEVEL]

## 3. Reserve: full H+position consistency for trigonal Te

**Gap.** A symmetric spectrum is insufficient for Berry/optical observables. The official symmetrization tutorial distinguishes H, position (`AA`), energy-weighted position (`BB`), orbital-moment (`CC`), and spin (`SS`) matrices, and provides a real nonmagnetic SOC Te example. This is directly adjacent to Hamiltonian-only symmetrization. [T1]

**Artifact.** `tutorials/5_symmetrization/Te_data/Te_tb.dat` is a complete 17.3 MB numeric starting file, not just the accompanying INCAR/POSCAR. Its header gives 24 WFs and 195 R vectors. Pair it with `Te.win`, structural information, spin-order convention, and lattice metadata. For this postprocessing task, do not bundle the adjacent `POTCAR` or require a VASP rerun. [TDATA]

**Reference.** The current route is `System_R.from_tb_dat(..., berry=True)`, `spin_block2interlace()` for this old spin-block-ordered dataset, `SymmetrizerSAWF.from_spacegroup_and_projections`, and `System_R.symmetrize2`. Bounded source targets are `system/system_R.py` and `symmetry/sym_wann_2.py`; the source documents phase convention I (`use_wcc_phase=True`). Preserve the position/center and nonsymmorphic translation conventions rather than treating position as an unrelated scalar H block. [T1, T2, T3]

**Pre-solution / oracle.** Give the unmodified H+position input, not a symmetrized model or final curvature plot. Compare operator covariance and a small declared Berry/optical calculation against the pinned reference. A useful diagnostic is H-only repair versus consistent H+position repair on the *same* input. Do not infer an orbital-magnetization reference from this `_tb.dat` alone: that requires additional BB/CC information. [T1, SYMLEVEL]

**Cautions.** The tutorial explicitly limits its original atomic-projection symmetrization method to non-maximally-localized input. Do not advertise it as discovering representations of arbitrary already-mixed MLWFs. Also, changing from GaAs to chiral Te alone is not computational diversity: **the core still contains group averaging**, so this is not my nominated pilot under the parent's latest constraint. [T1, T3]

## 4. Strong fallback: reconstruct spin-current input matrices for Pt

**Gap / independent core.** A Hamiltonian and its symmetry do not supply all operator matrix elements needed for spin Hall calculations. The official Pt tutorial reconstructs `.sHu` and `.sIu` from `.mmn/.spn/.eig` via a finite sum over intermediate Bloch states, then compares against matrices produced by `pw2wannier90`. This is a tensor-contraction / truncated-completeness problem, not orbital-representation averaging or gauge identification. Pt is a nonmagnetic heavy-metal SOC family, different from Fe and diamond. [PT1]

**Artifact.** The raw `.mmn/.spn/.eig` files in `tutorials/3_spin_hall/data_Pt/` total 11,920,055 B. Include `.win` for dimensions/conventions and, for the legacy conversion utility, `.amn`; that full input set is 13,776,960 B. The same official directory has direct `.sHu/.sIu` files, 14,168,152 B each. Keep those evaluator-side. [PTDATA]

**Reference boundary.** Prefer the current object-level methods in `w90files/wandata.py`: `set_sIu_from_mmn_spn`, `set_sHu_from_mmn_eig_spn`, and, if desired, `set_uHu_from_mmn_eig`. The old executable `utils/mmn2uHu.py::run_mmn2uHu` is still an official solution-bearing entry point, but its file-writing workflow and notebook invocation must be checked against the pin. The current Fe regression test `tests/test_mmn2uhu.py` exercises all four constructed operator families and compares its reference arrays at absolute tolerance `1e-10`. [PT2, PT3, PT4]

**Pre-solution / oracle.** Freeze real input operators and a declared intermediate-band cutoff; ask for the missing spin-overlap/energy-weighted-spin-overlap matrices. Build the numerical oracle by running the exact upstream contraction at that cutoff. Direct DFT `.sHu/.sIu` are a separate physics comparison: **a finite-band completeness approximation is not entitled to exact agreement with the direct DFT matrices**, and an SHC curve difference is not automatically an implementation error. The official tutorial explicitly investigates that comparison. [PT1, PT3]

**Readiness.** Data and reference entry points are verified. A bounded contraction task avoids full BZ integration, smearing/grid-convergence ambiguity, plotting, and heavy package extras. It is the best fallback if the parent prefers a continuous operator task to EBR enumeration. No reference output was generated during this research.

## 5. Reserve only: smooth submanifold gauges / MRWF

**Gap.** Separating a joint Wannier model into valence/conduction or other energy-separated target manifolds requires more than band sorting: the separated gauges must remain smooth and the orbitals localized. The MRWF paper supplies parallel transport plus localization, with applications to Si, the top valence band of MoS2, and SrVO3 d submanifolds. This is distinct from VASP2KP's local representation matching, but still too close to the parent's gauge territory to nominate here. [MR]

**Concrete reference.** `Wannier.jl/src/localization/split.jl`, `src/localization/parallel_transport/parallel_transport.jl`, and `contraction.jl`; use `test/localization/split.jl`, not an unpinned example notebook. The transport implementation requires a Cartesian k grid and six axial neighbors. It also contains obstruction-matrix eigenvalue/logarithm handling, so this candidate is not a clean answer to “no eigendecomposition core.” [JL, JTEST, JPT]

**Download verified.** The official `Artifacts.toml` resolves `Si2_coarse.tar.gz`; the downloaded archive's SHA256 is `0ea12d3ffb620efe7b4f4297a397904864d594dec5cc0d82fc4319182ee1e46f`, matching the manifest. It contains `Si2.amn/.mmn/.eig/.win`, joint-model `outputs/Si2.chk`, and separate `valence/` and `conduction/` reference directories. [JDATA]

**Pre-solution split.** The unsplit joint gauge/checkpoint is a valid input *for a remixing task*, even though it is the output of an earlier Wannierization stage. Hide the valence/conduction `.vmn`, `.amn`, and overlap references. Grade subspace orthogonality, smoothness/periodicity, and interpolation rather than individual gauge phases. Keep the full 944.1 MiB `MRWF_export_20230526.aiida` archive out of a small pilot; the verified 37.8 MB Julia fixture already exercises the implementation. The MoS2/SrVO3 physical-family extensions are paper-grounded but were **not** separately downloaded or qualified here. [JTEST, MRDATA]

## Other follow-ups checked, but not promoted

- **PDWF / robust projectors:** a genuinely important automated-projection follow-up, already represented in later Wannier90 releases. The 2023 v2 archive is 31.0 GiB including a 15.2 GiB AiiDA export. The 2025 robust magnetic/SOC dataset provides a 327.1 MiB magnetic raw-I/O bundle and a 268.6 MiB magnetic AiiDA archive, alongside much larger SOC/benchmark bundles. Its 20.6 KiB `projectors_specifications.json` is metadata, not a replacement for wavefunction/projection data. The record advertises a newer version; the newer record did not resolve through the browsing interface during this audit, so the quoted sizes are specifically the inspected July 10, 2025 v1. Do not promote this to a small execution task based on JSON filenames alone. [PD, PDDATA, ROBUST]
- **symWannier:** official, solution-bearing and closely relevant to SAWF; its README requires QE >=7.3 for `irr_bz` inputs and identifies `.immn/.iamn/.ieig/.isym` plus `symwannier wannierize -S`. The paper's on-request data statement is weaker than the directly downloadable WannierBerri Fe fixture, hence the latter is preferred. [SYMW, KOR]
- **WannSymm magnetic examples:** official MnF2, CrO2, K2Cr3As3, and Ce3Pd3Bi4 examples are genuine different families, but their advertised central operation is again real-space Hamiltonian symmetrization/character analysis with atomic-like angular dependence. Changing material alone does not satisfy the parent's independent-core requirement. [WS]
- **Bulk/slab MLWF stitching:** arXiv:1901.04259 is relevant to genuine cross-model gauge mismatch. I did not verify an author-hosted small downloadable paired bulk/slab fixture plus executable reference in this pass. Do not replace that missing evidence with a fabricated random gauge-rotation benchmark. [STITCH]

## Handoff / bounded next action

If assigned one builder task, start with **candidate 1 only**. Reproduce the official diamond test, export its pre-enumeration integer feature tables with raw-input provenance, and retain the upstream enumeration as the private oracle. Preserve all k-point constraints and require the complete feasible set. If the one-time symmetry preprocessing proves unexpectedly difficult, candidate 4 is the next bounded numerical choice; it already has real Pt input and direct operator-reference files.

Do not count candidate 3 as an independent group-average pilot; do not duplicate VASP2KP with candidate 5. No claim of runtime, numerical success, or completed pilot is made here.

### Useful integrity anchors

| File | SHA256 |
|---|---|
| `wannier-berri/tests/data/diamond/diamond.sawf.npz` | `5d7afe1c0ece7631211b54c5feddea3799d4793ffb7416215735d5c152d3ea14` |
| `wannier-berri/tests/data/diamond/diamond.eig` | `3e9395be4a98eb3da969a077a50b53d07d57d7acdb289642822ff8641551e7c7` |
| `wannier-berri/tests/data/diamond/diamond.win` | `1bbb1843e5933e79fed4e5a477641ce7cc8e3521f4102ffcf2060663e4a940ef` |
| `WannierBerri-tutorial/tutorials/5_symmetrization/Te_data/Te_tb.dat` | `5a9f95f14535dfa894901c8ae2ca86897b5a9e3ad6787ef46cc4b12282c3bacf` |
| `Si2_coarse.tar.gz` | `0ea12d3ffb620efe7b4f4297a397904864d594dec5cc0d82fc4319182ee1e46f` |

## Primary-source index

All repository paths in this note refer to these immutable snapshots unless a release/documentation URL is explicitly given. Data sizes and hashes were measured on the downloaded copies. Download individual git-tracked files by replacing GitHub `/blob/` URLs with the corresponding `raw.githubusercontent.com/OWNER/REPO/COMMIT/PATH` URL; no authenticated API or package installation is needed.

- **[BASE]** Original paper: https://arxiv.org/abs/1805.12148 ; full text https://arxiv.org/pdf/1805.12148 .
- **[WB]** Official WannierBerri source pin: https://github.com/wannier-berri/wannier-berri/tree/e046ddc4bfe026ba1f9af2376f04babac5677425 .
- **[TUT]** Official tutorial source pin: https://github.com/wannier-berri/WannierBerri-tutorial/tree/efe56e5b312a903bdbf06dcfc7b5fb8bb44c2afb .
- **[JL]** Author's MRWF implementation pin: https://github.com/qiaojunfeng/Wannier.jl/tree/ae4368abe60f7d6167c9e783e8aafca235038f10 .
- **[WBPY]** Maintainer's current package metadata: https://pypi.org/project/wannierberri/ ; machine-readable https://pypi.org/pypi/wannierberri/json .
- **[WBREL]** Official GitHub releases: https://github.com/wannier-berri/wannier-berri/releases ; queried https://api.github.com/repos/wannier-berri/wannier-berri/releases/latest .
- **[W90REL]** Official releases and timestamp: https://github.com/wannier-developers/wannier90/releases ; https://api.github.com/repos/wannier-developers/wannier90/releases/latest .
- **[JLREL]** https://github.com/qiaojunfeng/Wannier.jl/releases ; https://api.github.com/repos/qiaojunfeng/Wannier.jl/releases/latest .
- **[ENV]** https://github.com/wannier-berri/wannier-berri/blob/e046ddc4bfe026ba1f9af2376f04babac5677425/pyproject.toml .
- **[P1]** Official initial-projection tutorial: https://tutorial.wannier-berri.org/tutorials/7_find_projections/find_projections.html .
- **[P2]** Search implementation: https://github.com/wannier-berri/wannier-berri/blob/e046ddc4bfe026ba1f9af2376f04babac5677425/wannierberri/symmetry/projections_searcher.py .
- **[P3]** Band/Wannier symmetry handling: https://github.com/wannier-berri/wannier-berri/blob/e046ddc4bfe026ba1f9af2376f04babac5677425/wannierberri/symmetry/sawf.py ; trial-orbital definitions: https://github.com/wannier-berri/wannier-berri/blob/e046ddc4bfe026ba1f9af2376f04babac5677425/wannierberri/symmetry/projections.py .
- **[P4]** Exact tested windows and assertions: https://github.com/wannier-berri/wannier-berri/blob/e046ddc4bfe026ba1f9af2376f04babac5677425/tests/test_find_projections.py .
- **[D1]** Raw diamond numerical data: https://github.com/wannier-berri/wannier-berri/tree/e046ddc4bfe026ba1f9af2376f04babac5677425/tests/data/diamond/di.save .
- **[D2]** Direct small cache download: https://raw.githubusercontent.com/wannier-berri/wannier-berri/e046ddc4bfe026ba1f9af2376f04babac5677425/tests/data/diamond/diamond.sawf.npz .
- **[D3]** Fe frozen-window SAWF inputs: https://github.com/wannier-berri/wannier-berri/tree/e046ddc4bfe026ba1f9af2376f04babac5677425/tests/data/Fe-444-sitesym .
- **[S1]** SAWF tests and numerical references: https://github.com/wannier-berri/wannier-berri/blob/e046ddc4bfe026ba1f9af2376f04babac5677425/tests/test_wannierise.py .
- **[S2]** Wannierization implementation: https://github.com/wannier-berri/wannier-berri/blob/e046ddc4bfe026ba1f9af2376f04babac5677425/wannierberri/wannierisation/wannierise.py .
- **[SYMLEVEL]** Official distinction between point-group reduction, operator symmetrization, and SAWF: https://docs.wannier-berri.org/en/master/symmetries.html .
- **[KOR]** Koretsune, *Construction of maximally-localized Wannier functions using crystal symmetry*, CPC 285, 108645 (2023): https://www.sciencedirect.com/science/article/pii/S0010465522003642 .
- **[SYMW]** Author's implementation and file requirements: https://github.com/wannier-utils-dev/symWannier .
- **[T1]** Official Te/Fe operator-symmetrization tutorial and its limitations: https://tutorial.wannier-berri.org/tutorials/5_symmetrization/tutorial_symmetrization-solution.html .
- **[T2]** System/operator conventions: https://github.com/wannier-berri/wannier-berri/blob/e046ddc4bfe026ba1f9af2376f04babac5677425/wannierberri/system/system_R.py .
- **[T3]** Real-space operator symmetrizer: https://github.com/wannier-berri/wannier-berri/blob/e046ddc4bfe026ba1f9af2376f04babac5677425/wannierberri/symmetry/sym_wann_2.py .
- **[TDATA]** Direct H+position data: https://raw.githubusercontent.com/wannier-berri/WannierBerri-tutorial/efe56e5b312a903bdbf06dcfc7b5fb8bb44c2afb/tutorials/5_symmetrization/Te_data/Te_tb.dat .
- **[PT1]** Official spin-Hall tutorial, including the sum-over-states reconstruction and comparison: https://tutorial.wannier-berri.org/tutorials/3_spin_hall/solution/tutorial_spin_hall.html .
- **[PTDATA]** Real Pt input and direct operator-reference directory: https://github.com/wannier-berri/WannierBerri-tutorial/tree/efe56e5b312a903bdbf06dcfc7b5fb8bb44c2afb/tutorials/3_spin_hall/data_Pt .
- **[PT2]** Current construction entry points: https://github.com/wannier-berri/wannier-berri/blob/e046ddc4bfe026ba1f9af2376f04babac5677425/wannierberri/w90files/wandata.py .
- **[PT3]** Legacy standalone conversion reference: https://github.com/wannier-berri/wannier-berri/blob/e046ddc4bfe026ba1f9af2376f04babac5677425/wannierberri/utils/mmn2uHu.py .
- **[PT4]** Operator-construction regression test: https://github.com/wannier-berri/wannier-berri/blob/e046ddc4bfe026ba1f9af2376f04babac5677425/tests/test_mmn2uhu.py .
- **[MR]** Qiao et al., *Automated mixing of maximally localized Wannier functions into target manifolds*: https://www.nature.com/articles/s41524-023-01147-9 ; https://arxiv.org/abs/2306.00678 .
- **[JTEST]** Official real-data tests: https://github.com/qiaojunfeng/Wannier.jl/blob/ae4368abe60f7d6167c9e783e8aafca235038f10/test/localization/split.jl .
- **[JPT]** Transport kernel: https://github.com/qiaojunfeng/Wannier.jl/blob/ae4368abe60f7d6167c9e783e8aafca235038f10/src/localization/parallel_transport/parallel_transport.jl .
- **[JDATA]** Author's pinned dataset/checksum manifest: https://github.com/qiaojunfeng/Wannier.jl/blob/ae4368abe60f7d6167c9e783e8aafca235038f10/Artifacts.toml ; downloaded https://huggingface.co/datasets/atomology/WannierDatasets/resolve/artifacts/Si2_coarse.tar.gz .
- **[MRDATA]** Full paper-data record and file inventory: https://archive.materialscloud.org/records/gqaqd-ckn07 ; DOI https://doi.org/10.24435/materialscloud:2f-hs .
- **[PD]** Projectability-disentanglement paper: https://www.nature.com/articles/s41524-023-01146-w .
- **[PDDATA]** v2 data inventory: https://archive.materialscloud.org/records/fnssr-dhs62 ; DOI https://doi.org/10.24435/materialscloud:x0-yf .
- **[ROBUST]** Inspected robust magnetic/SOC PDWF dataset v1, July 10, 2025: https://archive.materialscloud.org/records/tc8pz-ddy75 ; DOI https://doi.org/10.24435/materialscloud:9g-ds ; advertised newer-version resolver https://archive.materialscloud.org/records/tc8pz-ddy75/latest .
- **[WS]** Official WannSymm source/examples: https://github.com/ccao/WannSymm ; author paper https://www.sciencedirect.com/science/article/pii/S0010465521003088 .
- **[STITCH]** Lihm and Park, *Reliable methods for seamless stitching of tight-binding models based on maximally localized Wannier functions*: https://arxiv.org/abs/1901.04259 .
