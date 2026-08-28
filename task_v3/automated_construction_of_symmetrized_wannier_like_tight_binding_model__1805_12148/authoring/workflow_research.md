# Workflow/data research sidecar: arXiv:1805.12148

Research date: 2026-08-28 UTC / 2026-08-27 America/Los_Angeles.

Scope: original paper and supplemental availability; official `aiida-tbextraction` and `symmetry_representation` histories, issues, and downloadable fixtures. TBmodels history belongs to the parent; adjacent methods belong to the other researcher. **No pilots, scientific calculations, dependency installations, or test executions were performed.** Inspection included Git history, archive listings, text inputs, and read-only HDF5 metadata.

## Decision for the parent / pilot03 builder

**Do not choose a repair of the original strained-model or g-factor discrepancy yet.** There is a reported discrepancy but no verified corrected model, g-tensor implementation, or accessible full strain-data archive in this investigation. Experimental agreement must not be substituted for an executable implementation oracle.

The strongest verified contributions are **components for the parent's historical import/cell/symmetry pipeline**: real III-V representation matrices, legacy serialization fixtures, a strained-structure compatibility reference, and later genuine fixes. A second useful component is a later positional-quality evaluator with a numerical reference on an existing silicon model. Neither should be advertised as a difficult standalone task without independent bottlenecks from the larger pipeline. Evidence and exact artifacts follow in sections 2–4.

For a separate pilot03, **prefer neighboring device-scale software if that sidecar has already verified a source implementation and achievable numerical reference**. I have not independently verified that candidate. Same-direction strain interpolation becomes a defensible fallback only after acquiring direct intermediate-strain models. The original window-search tests are weaker than their names suggest: they do not establish an optimized numerical outcome. See G3.

## 1. Original-paper facts and what they do not establish

Primary sources:

- Paper record and versions: <https://arxiv.org/abs/1805.12148>. v1: May 30, 2018; v2: October 5, 2018.
- Paper PDF: <https://arxiv.org/pdf/1805.12148v2>.
- Published paper: <https://doi.org/10.1103/PhysRevMaterials.2.103805>; publication date October 30, 2018, confirmed by <https://journals.aps.org/prmaterials/recent?page=267>.
- Author-hosted published PDF: <https://greschd.ch/assets/pdf/gresch_automated_2018.pdf>.

Compact evidence ledger from the paper:

| ID | Directly reported evidence |
| --- | --- |
| P1 | Table I: unstrained SWTB g-factors InSb −49.8, InAs −15.3, GaSb −15.1; experimental comparisons −50.6, −15, −7.8. Perturbative and Landau-level calculations agree within 0.5%. |
| P2 | Table I: SWTB masses `(SO,LH,HH,e)` are InSb `(0.118,0.016,0.219,0.015)`, InAs `(0.118,0.036,0.340,0.029)`, GaSb `(0.124,0.039,0.20,0.036)`. Masses use a quadratic fit over 0.001 inverse angstrom. |
| P3 | Table II: band-mismatch initial→optimized is InSb `0.107→0.033`, InAs `0.113→0.046`, GaSb `0.082→0.043`. InSb windows change from `(-4.5,[-4,6.5],16)` to `(-4.44,[-3.24,8.67],14.01)` eV. |
| P4 | Figure 8 explicitly flags disagreement for the L-point conduction band at −4% biaxial (111) strain. Its caption does not identify a corrected solution. |
| P5 | Figure 7 compares direct 2% biaxial-(001) InSb with interpolation between 1% and 3%. Section IV.C warns against mixing strain directions. |
| P6 | Section IV.D / supplemental reference advertises numerical strain-energy tables, an AiiDA provenance export, and 195 strained models. |

**Interpretation, not a result:** P1's experimental discrepancy is not a code-regression target. P4 supplies a real material-specific failure to investigate, but not its cause or an achievable repair oracle. P5 is an example of successful interpolation, not evidence that a general interpolation baseline fails. P3 alone is insufficient to identify the exact archived calculation and recreate its metric conventions.

## 2. Downloadable-data audit

### 2.1 Paper source and supplemental access

Downloaded and listed <https://arxiv.org/src/1805.12148v2> as `/tmp/workflow-research-180512148/arxiv-source.tar`. Its ten members are:

```text
high_throughput_tb.bbl
high_throughput_tb.tex
hopping_weights.pdf
optimize.pdf
strain_band_shift.pdf
strain_interpolation.pdf
strain_workflow_diagram-crop.pdf
symmetrize_nonsymmorphic.pdf
vasp_workflow_diagram-crop.pdf
workflow_diagram-crop.pdf
```

**There is no model archive or machine-readable strain table in that downloaded source bundle.** The arXiv bibliography still uses `[URL]` placeholders for its three supplemental references; use the published-paper supplement route instead.

Attempted official routes:

- <https://journals.aps.org/prmaterials/supplemental/10.1103/PhysRevMaterials.2.103805>: shell request returned HTTP 403; web browsing supplied no usable listing.
- <https://link.aps.org/supplemental/10.1103/PhysRevMaterials.2.103805>: no usable listing through browsing.
- <https://harvest.aps.org/v2/journals/articles/10.1103/PhysRevMaterials.2.103805>: metadata request returned HTTP 401.
- The attempted `/supplemental` suffix on that Harvest endpoint returned HTTP 404. This is an attempted route, **not a discovered download URL**.
- ETH's official record <https://www.research-collection.ethz.ch/handle/20.500.11850/303467> is marked metadata-only.
- The author's publications listing <https://greschd.ch/publications/> links the paper PDF but did not supply a supplemental archive for this entry.

Thus archive names, byte sizes, member paths, and completeness of the advertised 195-model set remain **unverified**. This is an access limitation of this research run, not proof that the data have disappeared. Do not invent a `models.zip` filename or claim that the archive contains g-factor scripts.

### 2.2 Official workflow checkout: real starting inputs and recorded outputs

Repository: <https://github.com/greschd/aiida-tbextraction>.

Local checkout: `/tmp/workflow-research-180512148/aiida-tbextraction`.

Inspected default `develop` commit: `6b51cd6fce8feaea6c7a9235a49073a2500eead3` (November 16, 2020). Immutable tree: <https://github.com/greschd/aiida-tbextraction/tree/6b51cd6fce8feaea6c7a9235a49073a2500eead3>.

| Path relative to checkout | Bytes / inspected contents | Use |
| --- | --- | --- |
| `tests/data/wannier_input_folder/aiida.amn` | 5,661,030; VASP header identifies unstrained InSb; dimensions 36 bands, 216 k-points, 14 projections | Genuine pre-Wannierization input |
| `tests/data/wannier_input_folder/aiida.mmn` | 82,906,086; header 36 bands, 216 k-points, 8 neighbors | Genuine overlap input |
| `tests/data/wannier_input_folder/aiida.eig` | 365,472 | Actual input energies, preferable to mocked validity bands |
| `tests/data/bands.hdf5` | 9,816; `eigenvals` shape `(11,14)`, k-points `(11,3)` | Small stored reference-band dataset |
| `tests/data/symmetries.hdf5` | 157,536 | Symmetry input for InSb workflow tests |
| `tests/data/InSb/POSCAR` | 323 | Unstrained InSb structure |
| `tests/evaluate_model/data/silicon/model.hdf5` | 266,032; eight-orbital model, complex `(8,8)` hoppings, positions `(8,3)`, cell `(3,3)` | Later quality-evaluation reference |
| `tests/evaluate_model/data/silicon/bands.hdf5` | 9,288 | Silicon reference bands |
| `tests/evaluate_model/data/silicon/si_uc_different.cif` | Present | Deliberately nonmatching-cell validation fixture |

Seven `tests/mock_codes_data/mock-wannier90-*/` directories contain recorded `aiida_hr.dat`, `aiida.win`, `aiida.wout`, `aiida_centres.xyz`, `aiida_wsvec.dat`, and `aiida.eig` files. Each `aiida_hr.dat` is 2,735,675 bytes. Exact directory suffixes:

```text
a77205373725c24b166d84021355549b
57e036f8b59a3f4a0c08fa95d127f5b9
4f4b1c2f6fbe2abc41aa51898b6a265a
ec2dad7dcde111febd0730b2a094485e
e8391fbc96eda51713be449b88128d04
45091aacae0d16a2edbb0885bbd408a5
b055d309ad3957386679e90d1c496e64
```

Important distinction: these are **recorded outputs used by mock-code tests**, not seven verified optimized paper models. Read each accompanying `.win` before assigning a physical calculation to it. No equality to P1–P3 has been established. The tutorial explicitly warns that its QE/PBE example does not accurately describe InSb and is not a hybrid-functional reproduction: <https://aiida-tbextraction.readthedocs.io/en/latest/tutorial/example.html>.

Public historical availability is directly supported by commits `b57112811b51a7ee31a480af47a034f23fed60f5` and `2668c3570d4662d8a8612ae5ca34bc6277a8bbcb` (December 4, 2019; introduce recorded Wannier/run-window and window-search outputs). The input paths above are present by `af5d2111bded5d0c04b90620b1c5d0bce51880ec` (December 6, 2019). These are legitimate starting artifacts for later 2020 workflow fixes, not newly generated fixtures.

### 2.3 Official symmetry checkout: strongest small real-material references

Canonical repository linked by the official documentation: <https://github.com/Z2PackDev/symmetry_representation>. Do not assume the repository is named `greschd/symmetry-representation`.

Local checkout: `/tmp/workflow-research-180512148/symmetry_representation`.

Inspected `develop`: `defb21f66831b2314226469b8bdb68ef84b7855b` (April 29, 2020). Immutable tree: <https://github.com/Z2PackDev/symmetry_representation/tree/defb21f66831b2314226469b8bdb68ef84b7855b>.

| Path | Bytes / reference |
| --- | --- |
| `tests/samples/InAs_symops.json` | 11,350; stored real-space operations in reduced and Cartesian coordinates |
| `tests/samples/symmetries_InAs.hdf5` | 212,240; stored representation reference |
| `tests/samples/symmetries_old.hdf5` | 157,536; legacy serialization fixture |
| `tests/samples/symmetries.hdf5` | 178,144; newer serialization fixture |
| `tests/samples/POSCAR` | 323; unstrained compatibility fixture |
| `tests/samples/POSCAR_110_bi_0.04` | 274; strained compatibility fixture |

`tests/test_auto_repr.py::test_auto_repr` constructs a 14-orbital InAs basis, with In `s+p` and As `p` orbitals for each spin. It compares generated rotations, translations, antiunitary flags, and representation matrices to the stored HDF5 reference, using matrix tolerances of `1e-12`. This is a much stronger oracle than merely obtaining a finite matrix. The reference was introduced at `3001a307a8c9bc29c394a8c71d839c2755ab4257` (September 24, 2018).

`tests/test_compatible.py` supplies hard-coded compatible rotations for the strained fixture and asserts five retained entries from its particular input list. **Five is a fixture-list count, not a claim about the order of the complete strained crystal symmetry group.** The relevant fixture/test history reaches `32315cc6f9256b08a34990cbcf999232af3e7408` (August 19, 2017). These tests also cover filtering nested symmetry containers.

## 3. Genuine later histories and issues

### 3.1 Symmetry representation

All commit links use `https://github.com/Z2PackDev/symmetry_representation/commit/<SHA>`.

| Later commit | Public pre-solution parent | Actual change / value |
| --- | --- | --- |
| `3bd9a83851382439427537c310647600283560de` | `2e831d80c28fa447e287569a239417f1a4562b45` | April 29, 2020: clips slightly out-of-range rotation traces before inverse cosine, separately for proper and improper rotations; rejects materially invalid traces. Fixes official issue #10 via PR #11. |
| `f65ac1562c0b9dcfb5bc06ea9fc26581412f5da6` | `e81235dcad08f0a6e0ebcf2e9749e79e0e8c7de4` | March 5, 2020: repairs deprecated HDF5 `.value` usage in legacy loading. |
| `e81235dcad08f0a6e0ebcf2e9749e79e0e8c7de4` | `5dffe010b0fc147f496e98afa8e63dee8847f8fe` | March 2, 2020: registers an entry point for `fsc.hdf5-io`. |
| `a45ac2973a7a8ca3fbf8f55fc702cc6bd54ac05c` | `6d1f068ea91177576f5a437e79858a47643f006c` | December 19, 2018: representation serialization compatibility when `numeric` is absent. |
| `bdcd0e8d347cf9b5ecccd6a61ce0086379dfadab` | `b2a24c20252db409961f3638826dacb05395c5c1` | October 30, 2018: configurable position tolerance in automatic representation construction. |

Useful primary issues:

- <https://github.com/Z2PackDev/symmetry_representation/issues/10>: actual numerical-domain failure, not a speculative stress case. This fix alone is too small for a hard task.
- <https://github.com/Z2PackDev/symmetry_representation/issues/3>: WS2 orbital-normalization problem; maintainers distinguish inconsistent normalization from a basis not closed under the requested symmetries. Do not indiscriminately normalize an incomplete basis and call the result correct.
- <https://github.com/Z2PackDev/symmetry_representation/issues/12>: d-orbital threefold rotations; maintainer explains the unit-sphere relation and orbital conventions. A user supplies a numerical workaround but explicitly says the resulting representations were **not checked for correctness**. It is not a verified strong solution.
- <https://github.com/Z2PackDev/symmetry_representation/issues/2>: numerical/symbolic matrix mixing has inconsistent shapes. The issue remains open in the inspected API listing; do not claim a complete later fix.

### 3.2 Workflow construction, quality metrics, and strain routing

All commit links use `https://github.com/greschd/aiida-tbextraction/commit/<SHA>`.

| Later commit | Public pre-solution parent | Actual change / value |
| --- | --- | --- |
| `39bdd099fc3c9f36768dab24154c9f516aab75fa` | `06ccef96b5c452cc3a943ea0d513df3293076ebc` | October 28, 2020: fixes forwarding the modified structure to QE sub-workchains. Commit message explicitly says the previous interface change broke strained workflows. Updates three workflow modules and corresponding fixtures/tests. |
| `990750da3906b0a0857b58998161fc320691ecb4` | `9bbb2bb120ec07a1bf843a34c4603ee3ae37477f` | March 30, 2020: adds `CombinedEvaluation`. |
| `6c73872ae5e28d17e0a0baf0205150e7c982362b` | `990750da3906b0a0857b58998161fc320691ecb4` | March 30, 2020: adds orbital-to-atom positional evaluation, later named `MaximumOrbitalDistanceEvaluation`. |
| `61c591f6df0e517a529fefd75dd16f226ce05ddd` | `dc4a3c0be7b238753ad04d42291fc28e02d81a66` | March 4, 2020: accounts for excluded bands in QE Wannier input. |
| `2195ea519bca4f2969819610343c0aefd95842c6` | `af84272e8da638b0e29b1ca69323d2ccb74fdc2b` | March 27, 2020: fixes the no-reduction case. |
| `40ab47aa8c8d037ed41f32b0399f9abe5b3cf636` | `61c591f6df0e517a529fefd75dd16f226ce05ddd` | March 27, 2020: propagates exposed inputs to parse/slice/symmetrize stages. |

The strain-routing implementation paths are `aiida_tbextraction/fp_run/_qe_run.py`, `fp_run/reference_bands/_qe.py`, and `fp_run/wannier_input/_qe.py`. This is a documented workflow bug, **not evidence that the original 2018 VASP results were computed using the wrong strain**.

Official issues exposing remaining integration gaps:

- <https://github.com/greschd/aiida-tbextraction/issues/16>: interrupted QE can leave partial `output_band`; asks for k-point-count consistency checking. No verified completion found.
- <https://github.com/greschd/aiida-tbextraction/issues/18>: VASP compatibility described as untested and likely broken. Avoid promising an easy current-stack reproduction of the original VASP workflow.
- <https://github.com/greschd/aiida-tbextraction/issues/22>: split `pw2wannier90` collection is performed inside a workchain; cached replay can fail after remote directories disappear. No verified completed reference found.
- <https://github.com/greschd/aiida-tbextraction/issues/23>: genuine example-run failure loading a symmetry HDF5 file, ultimately showing a string/`.decode` exception in `fsc.hdf5_io`. This is **distinct** from the `.value` deprecation fix above. Do not attribute its repair to `f65ac15` without inspecting the dependency fix.

Branch warning: the clone's default `develop` stops at `6b51cd6`, but remote `split_pw2wannier_workflow` reaches `25607ed3f57b0a27f6253277514e508d73d240f3` (February 25, 2021). Its split-conversion code is not in that default checkout. Do not silently combine branches into an allegedly historical baseline.

## 4. Ranked gap ideas, references, and independent bottlenecks

### G1 — Real III-V import → representation → symmetry-compatible model pipeline

**Priority A as a component of parent's candidate (1), not a second duplicate pilot.**

- **Starting artifacts:** choose the parent's genuine pre-fix TBmodels revision plus an explicitly pinned companion-library revision. Use the recorded InSb Wannier bundles and section 2.3's InAs/legacy/strained fixtures. Keep later reference code/data out of participant-visible solution material; do not fabricate a baseline by deleting working functions.
- **Strong reference:** stored InAs matrices and the official compatibility/serialization tests; later exact commits in section 3.1. The parent's TBmodels reference can supply Hamiltonian-level outcomes.
- **Observed baseline failures:** official numerical-domain and HDF5 compatibility issues; historical implementations available on both sides of fixes. No local execution has yet established the exact combination that fails together.
- **Independent bottlenecks:** orbital/spin ordering and phase conventions; reduced versus Cartesian operations and nonorthogonal cells; legacy typed serialization; unitary/antiunitary action; compatibility filtering after strain.
- **Proposed outcome:** recover reference matrices and retained operations, then satisfy the parent's independent spectral/model oracle. Do not count successful import alone as success.
- **Feasibility:** small CPU-only matrix references, no new DFT needed. Runtime compatibility still needs a pinned environment. A lone trace clamp or dependency pin is not a sufficiently hard task.

### G2 — Band agreement is not enough: positional-quality evaluation

**Priority A/B: strongest additional small numerical component found.**

- **Starting artifacts:** the public silicon HDF5 model, its bands, and structure fixture; historical workflow code before `990750d` / `6c73872`.
- **Strong later reference:** `tests/evaluate_model/test_band_difference.py` expects band cost approximately zero; `test_pos_distance.py` expects positional cost `0.79 ± 0.01` on the same model and exit status `300` for the supplied nonmatching unit cell. Later source implements both evaluators.
- **Baseline limitation:** the band score alone does not test the nonzero positional deviation measured by the second evaluator. This is a demonstrable metric blind spot, not proof that the fixture is a physically invalid model.
- **Independent bottlenecks:** periodic nearest-atom geometry; cell compatibility; heterogeneous evaluator inputs and outputs; cost weighting; preservation of diagnostic outputs in synchronous and submitted workflows.
- **Proposed outcome:** match both existing numerical references and compose the official evaluators without losing their outputs. A participant must not be graded merely on adding a function name.
- **Feasibility / caveat:** no DFT or Wannier rerun. However, the official combined-evaluator test applies the zero-valued band evaluator twice, so it **does not provide a nonzero weighted trade-off oracle or prove better optimized models**. Any richer optimization claim needs a separately verified reference, not newly invented expected numbers.

### G3 — Constrained energy-window optimization and ablation on real InSb inputs

**Priority B, conditional; not currently a strong standalone optimizer benchmark.**

- **Starting artifacts:** section 2.2's real `.amn/.mmn/.eig`, the reference bands, initial window from P3, and historical `RunWindow` / `WindowSearch` source.
- **Available reference:** later workflow implementation, seven recorded Wannier outputs, and P3's reported improvement. None has yet been matched into a verified end-to-end numerical optimizer oracle.
- **Critical test audit:** `tests/energy_windows/test_window_search.py` replaces validity-check energies with 14 zeros at every k-point, expressly to make every window valid; its result assertions only check that `cost_value`, `tb_model`, `window`, and `plot` exist. It uses `window_tol=1.5`, `num_iter=0`, and `dis_num_iter=1000`. These assertions cannot validate real optimization quality.
- **Actual constraint reference:** `RunWindow.window_valid` requires sorted endpoints, at most `num_wann` states in the inner window at every k-point, and at least `num_wann` states in the outer window at every k-point. Invalid windows return the large finite sentinel `314159265358979323`; tests only require cost above `1e10`. This is intentional behavior, not automatically a numerical bug.
- **Independent bottlenecks:** real per-k-point state counts; excluded-band bookkeeping; energy alignment and band selection; parse/slice/symmetrize ordering; evaluation after post-processing; robust optimization around invalid regions.
- **Necessary authoring gate:** run genuine Wannier90 against the existing raw inputs with a pinned successful implementation; verify a numerical final outcome and at least one independent ablation. Recorded mock outputs cannot answer arbitrary new window queries. Until then, restrict reuse to fixed-input import/post-processing validation.

### G4 — Strained structure must reach every downstream calculation

**Priority B: genuine solved integration gap, but an orchestration task rather than a physical-model repair.**

- **Public baseline / solution:** exact parent and fix for `39bdd099...` in section 3.2; `tests/test_optimize_strained_fp_tb.py` supplies an official strain workflow fixture.
- **Failure:** the commit documents loss of the intended structure when QE calculations were replaced by nested workchains. This establishes a real pre-solution failure without conjecturing a materials discrepancy.
- **Independent bottlenecks:** namespace forwarding through SCF/reference-band/Wannier stages; association of structures with symmetry filtering; consistent cell/reference-band metadata; per-strain provenance rather than accidental reuse.
- **Reference outcome:** compare the downstream structures and call inputs to the fixed source, with the stored strained compatibility fixture as an additional check. Do not claim numerical strained bands have been validated by a mocked provenance test.
- **Feasibility:** potentially inexpensive with recorded calculations, but the AiiDA environment is nontrivial. Adding issue #16's partial-band guard or #22's cache recovery would require new verified references; they are not automatically covered by the existing strain fix.

### G5 — Held-out, symmetry-consistent strain interpolation

**Priority C until direct-model artifacts are accessible.**

- **Natural start / hidden answer:** endpoint models as inputs; independently calculated intermediate-strain models as hidden references. P5 establishes an appropriate original-data split if those exact archive members can be recovered.
- **Baseline status:** the published example succeeds. No verified failure of a genuine implementation on available endpoint/intermediate models was found here.
- **Independent bottlenecks:** consistent basis and energy zero; matching lattice-vector/hopping support; strain-dependent cell and orbital coordinates; symmetry-subgroup consistency; handling band crossings when measuring errors.
- **Proposed outcome:** agree with withheld direct-model band energies and low-energy derivatives across several real intervals, while enforcing the target crystal's symmetry. Thresholds must be calibrated from actual independent models, not from an interpolator compared with itself.
- **Stop rule:** no artificial random gauge corruptions, manufactured hopping models, or invented multidirectional-strain truths solely to create difficulty. Without real intermediate models, this is not ready for pilot03. The small compatibility fixture alone does not validate interpolation of a strained Hamiltonian.

### G6 — Explain and repair the endpoint L-valley discrepancy

**Priority C / hold.**

- **Motivation:** P4 is an explicit original-paper discrepancy, stronger motivation than a generic robustness wish.
- **Starting artifacts needed:** exact endpoint model, corresponding first-principles energies, raw Wannier inputs and full window/post-processing provenance from the advertised export.
- **Missing strong reference:** no later corrected model or official correction implementation verified.
- **Independent diagnosis questions:** does error originate in band selection/disentanglement, the symmetry projection, the energy convention, or model-basis expressivity? These are hypotheses, not established causes.
- **Feasibility gate:** first reproduce the discrepancy from accessible data, then identify a successful source-grounded repair. Original-model reproduction alone cannot grade a claimed correction. Re-running unavailable first-principles work would materially change cost and setup requirements.

### G7 — Effective-mass / g-tensor band-selection or downfolding integration

**Priority C / hold from this sidecar; parent's #114 research may change this.**

- **Available numerical checks:** P1 and P2; no machine-readable strained g-tensor table or original perturbative/Landau implementation was located in the scoped repositories.
- **Search scope actually checked:** text/code/doc files in both cloned repositories; official issue listings; paper/source archive; author publication links. This is not a claim that no such code exists anywhere or inside the inaccessible supplement.
- **Independent bottlenecks:** selection of a separated target subspace; degenerate perturbation theory; derivative units and coordinate conventions; remote-band contributions; eigenvector gauge and tensor conventions.
- **Reference requirement:** an independently executable implementation or a verified table of sufficiently rich tensor/response outputs, in addition to actual model inputs. Scalar paper checks cannot uniquely validate a general g-tensor routine.
- **Critical distinction:** matching the SWTB calculation and correcting its agreement with experiment are different tasks. Do not set the experimental comparison as a software-unit-test expected value. Also do not assume the tutorial/PBE or test InSb model reproduces P1–P2 without provenance matching.

### G8 — Complete d-orbital representations under general rotations

**Priority C / reject as an immediate strong-reference task.**

- **Real failure source:** official symmetry issue #12; issue #3 supplies a related real WS2 normalization example.
- **Candidate starting artifacts:** user-provided reproducer and pre-fix official library code.
- **Independent bottlenecks:** normalized real spherical-harmonic conventions; polynomial identities on the unit sphere; orbital-subspace closure; symbolic versus numerical construction; spinful rotations.
- **Why not ready:** the proposed workaround is explicitly unverified, and no later complete official repair was found. A different library's independently checked rotation implementation could change this assessment, but that is adjacent-method research, not a result established here.

## 5. Practical handoff and evidentiary limits

1. **Immediately reusable:** copy or reference the small official InAs/symmetry/strained-compatibility fixtures for the parent's candidate (1); retain their immutable upstream URLs and intended basis order.
2. **Useful extra check:** the real silicon model's zero band cost versus nonzero positional cost supplies two distinct reference quantities. Keep the mismatch-cell failure fixture as a third, qualitatively different outcome.
3. **For pilot03:** use a separately verified device-scale reference if available. Do not let the existence of raw Wannier files be mistaken for an independently verified g-tensor or optimizer solution.
4. **Before reviving interpolation/discrepancy ideas:** obtain and list the actual APS archive; record checksums, concrete members, strain metadata, energy conventions, and whether outputs derive from direct first-principles calculations or interpolation. Do not download a large provenance export blindly before checking its listing/size.
5. **Baseline integrity:** use real historical commits/branches and artifacts that were public before the relevant later solution. Environment compatibility shims should be documented separately from the scientific repair. Do not bundle unrelated open issues into an allegedly solved reference.

Saved inspection evidence lives under `/tmp/workflow-research-180512148/`: the two full Git clones, `arxiv-source.tar`, `tbextraction-issues.json`, `symmetry-issues.json`, `symmetry-3-comments.json`, and `symmetry-12-comments.json`. The GitHub API listings include all returned open/closed issues and PRs. Some subsequent API requests were rate-limited; no conclusions rely on missing replies.

**Bottom line:** verified later source and strong small fixtures exist for symmetry/import/quality/strain-routing components. Original-paper discrepancy repair, full strained interpolation, and general g-tensor extraction do not yet have a verified achievable end-to-end reference from this scoped search. The inaccessible supplement is the main data limitation; weak mock optimizer assertions are a separate validation limitation.
