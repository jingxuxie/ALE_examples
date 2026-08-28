# Final report — no accepted frontier-hard task

**Disposition: REJECTED.** Four source-grounded pilots were built and tested with isolated fresh `ultima-alpha` sessions. Three are solved robustly. The fourth has a reproducible residual, but that residual depends on an under-specified repair convention rather than a demonstrated independent technical deficiency. The final scale search finds no valid counterexample to the solved device implementation.

No pilot meets the joint acceptance conditions: a complete public task, reference score above 0.90, fresh-agent core score below 0.70, and a genuinely unsolved central component. No production task is advertised as accepted. All pilots, source pins, references, submissions, logs and audits remain available for reproduction.

Audit date: **August 28, 2026 UTC**. Target: *Automated construction of symmetrized Wannier-like tight-binding models from ab initio calculations*, arXiv:1805.12148.

## 1. Candidate directions

The complete seven-field ledger—starting artifact, private solution artifact, outcome, shortcut, failure regime, independent bottlenecks, and checks—is `authoring/candidate_gaps.md`. Supporting source/history and feasibility research is in `authoring/adjacent_research.md` and `authoring/workflow_research.md`.

| Direction | Candidate gap and artifacts | Qualification / use |
|---|---|---|
| A: pre-fix/post-fix | Historical TBmodels Cartesian/atom assignment and cell-remapping code versus official later fixes and regression fixtures | Built in 01; genuinely repaired by the pilot agent |
| B: original/adjacent improvement | Hamiltonian-only atomic workflow versus later symmetry-aware position/response machinery; SAWF localization was another research lead | Operator branch built in 02; full localization not built |
| C: realistic scale | Bulk interpolation versus sparse open-device construction and stabilized lead modes | Built in 03 on approximately 7,500–11,000 orbitals |
| D: physical-family transfer | III–V/sp-style assumptions versus nonsymmorphic Te and magnetic Fe/d-orbital models | Built in 02; Fe transfer is solved |
| E: real-data model discrepancy | Direct band projection versus remote-band low-energy and magnetic response from actual ab-initio matrices | Built in 04 using Bi2Se3 and three TMD exports |
| F: multi-component integration | Wannier90/wsvec/coordinate semantics through cell transport; bulk hoppings through device/lead assembly | Built in 01 and 03 |
| G: ablation audit | Band-fit/window surrogate versus independent target-subspace and response checks | Original window-ablation route unqualified; independent response checks motivate 04, not a claimed repair of that original workflow |
| H: correctness/performance | Hamiltonian-only observables versus complete position-dependent responses; dense versus sparse/rank-aware transport | Built in 02 and 03 |

These are not eight variants of one simulator. They span historical defects, operator/gauge physics, inverse basis recovery, effective theories, transport, model selection and scale. Inaccessible supplementary archives and weak mocked optimizer assertions were recorded as evidence limitations, not silently replaced by invented labels. Unbuilt SAWF/EBR/Pymablock leads did not become extra pilots.

## 2. Four built pilots and private references

| Pilot | Participant-visible starting capability | Privileged solution / data |
|---|---|---|
| 01 `covariant_pipeline` | Actual historical defective method extracts with compatibility scaffolding | Official TBmodels fixes, pinned current infrastructure and full Si/Bi/InAs fixtures; 18 frozen cases |
| 02 `operator_response` | Hamiltonian-only atomic workflow, raw full H+position data and a complete observable interface | Pinned WannierBerri `sym_wann_2`, `System_R`, `evaluate_k` and formula modules; full Te and Fe author datasets |
| 03 `device_transport` | Adapted pre-supercell bulk interpolation, complete real hopping data, finite cells/gates/leads | Official Kwant 1.5.0 modes/scattering and independent Green-function controls, plus later TBmodels geometry |
| 04 `effective_physics` | Explicitly adapted full-space/projection-only exporter, not falsely labeled an untouched historical snapshot | Official VASP2KP 1.1.5 modules, commit `db38afc28eee209710c75388e1474c1bccde21b2`; full 600–800-band author matrices; 42 stored cases |

TBmodels reference pin: `39d7eb096d809137373774ef6ba337fdf36349bc`. Pilot01 preserves the explicit-atom semantics with the official fixed method at `84cdd38d47243208b49c88e8e41c449201530df7`, rather than substituting the newer periodic-image semantics.

WannierBerri reference pin: `e046ddc4bfe026ba1f9af2376f04babac5677425`; tutorial/data pin: `efe56e5b312a903bdbf06dcfc7b5fb8bb44c2afb`. Exact files, hashes, installation versions and transformations are recorded in each private manifest and `authoring/pilot0*_notes.md`.

No hard reference solution was invented from scratch. Official later/adjacent implementations produce the privileged outputs. Adapted public interfaces, compatibility shims and legitimate transformations are identified explicitly. No task statement mentions the paper or distributes reference outputs; public development inputs are unlabeled or invariant-only.

## 3. Reference, scale and scoring validation

- Every built reference scores approximately **1.000**. Source-independent checks include full-matrix geometry identities, finite-difference Berry/optical checks, scattering/Green-function agreement, current conservation, and exact finite-q spectral reduction.
- Pilot04's cubic truncation remainder decreases by approximately **16×** when q is halved; its Bi2Se3 magnetic eigenvalues agree with the author's printed values within **7.95e-5**, consistent with printed precision.
- Pilot03 retains every supplied hopping. Strong controls fit **90 seconds / 1 GiB**, with post-audit maxima **12.46 seconds / 217.51 MiB**. Direct dense complex128 allocations for 11,060 and 10,696 orbitals fail under that same cap; one matrix requires 1,866.51 and 1,745.67 MiB respectively. The submitted rank-aware sparse algorithm nevertheless solves these cases comfortably.
- Stored references, not repeated expensive author calculations, determine participant scores. Mean core score, worst family, component errors, runtime and memory remain in the JSON reports. Family shifts are not averaged away in decisions.
- Valid numerical scores use smooth reciprocal baseline-relative errors, without clipping or tolerance plateaus. Missing/invalid outputs receive no credit. A pre-grading audit corrected initially clipped scorers in 02/03; legacy and post-audit records are both retained. No cases, physical thresholds or component weights were changed to lower participant performance.

Useful validation records: `authoring/pilot04_independent_validation.json`, `authoring/dense_baseline_resource_probe.json`, pilot01's `private/validation/reference_validation_report.json`, pilot02's `private/reference/post_audit/audit_summary.json`, and pilot03's `private/reference/post_audit_summary.json`.

## 4. Valid fresh-agent tournament

All valid runs use the requested **`ultima-alpha`**, high reasoning effort, the provided allowlisted runner, empty attempt directories, read-only participant inputs, disabled web access and a **3,600-second cap**. Every valid run completes normally before the cap. Scores below use the final non-saturating evaluator.

| Pilot | Agent time | Test mean | Test worst family | Challenge mean | Challenge worst family |
|---|---:|---:|---:|---:|---:|
| 01 covariance | 15.62 min | 1.000000 | 1.000000 | 1.000000 | 1.000000 |
| 02 operator response | 13.64 min | 0.860326 | 0.860326 | 0.924982 | **0.849964, Te** |
| 03 device transport | 20.51 min | 1.000000 | 1.000000 | 1.000000 | 1.000000 |
| 04 effective physics | 14.04 min | 1.000000 | 1.000000 | 1.000000 | 1.000000 |

The near-one differences are roundoff, not meaningful hardness rankings. Operator response and device transport were the provisional two for counterexample auditing. The latter was selected for a remaining genuine scale question, not because its 1e-10 score difference established hardness. Covariance and effective physics were discarded as robustly solved, with complete attempted implementations and no substantive failure in their pools.

Raw evidence: `authoring/tournament/initial/runs.json`, `summary.json`, `scoreboard_test.json`, `scoreboard_challenge.json`, individual score reports, complete terminal logs and the four valid `attempt/` directories.

### Orchestration error, disclosed rather than hidden

An earlier set of four launches was interrupted after approximately **694 seconds** because the parent misread an early log snapshot as a stdin stall. The agents had actually begun work. This was a parent error, not a model failure. Those fragments were preserved, excluded from all scores and counterexample analysis, and hidden from replacement fresh agents. The replacement runs above each received a complete one-hour cap. Thus there were **four valid tournament runs plus four excluded interrupted launches**, not merely four process starts. Full provenance is in `authoring/launch_audit.md`, `authoring/tournament/interrupted_setup_01/` and each pilot's `private/interrupted_initial_attempt/`.

## 5. General methods and counterexamples

### 01 — completed historical repair, not a shortcut

The agent correctly handles Cartesian/nearest-atom semantics, complete WS-corrected hoppings and orbital-gauge-resolved cell transport. Sorted eigenvalues alone would fail the evaluator. Independent matrix sums, folding and randomized transport checks accompany the implementation. The public/private defect gap is real, but it is no longer frontier-hard for this model.

### 04 — complete general effective-theory solver

The agent implements real-linear unitary/antiunitary intertwiner recovery, polar correction, a canonical wave-operator expansion through cubic order and the orbital plus spin Zeeman term. It retains all remote bands. All material and complete-doublet challenge branches are solved. This is not a projected-spin or band-only shortcut; it is a successful general solution. Exact target–remote degeneracy would invalidate the reference too and was not added as a false counterexample.

### 02 — a real physical discrepancy, but an unfair failure region

The valid agent solves magnetic Fe and its response algorithm. The Te audit verifies physical errors of **1.2648% in Berry response** and **0.2768% in the optical kernel**; exact recentering controls remain invariant to about **1.55e-13**. The discrepancy is therefore not dismissed as a harmless common-origin gauge shift.

However, one under-specified repair choice explains it: projecting the complete position operator versus separately projecting the stored connection and centers. The source's convention was not sufficiently fixed by the public contract. An author-only diagnostic matching that convention raises the existing implementation's Te score to **0.997443**, **without changing the response code**. No second independent failure remains.

This is rejected as a basis for hardness or a ratchet. The 0.85 score must not be presented as an unsolved frontier capability. The original participant, valid submission, scores and confirmation metadata remain unchanged. See `authoring/pilot02_ratchet.md` and `private/reference/ratchet_audit/decision.json`.

### 03 — genuine scale probes also solved

The bounded counterexample search increases physically equivalent principal-layer groupings on the same full Si/InAs wires. It does not alter energies, tune to exact thresholds, add random defects or change the scoring limits. All **four reference-valid probes** are solved: minimum score **0.99999999776**, maximum participant cost **4.24 seconds / 196.16 MiB**.

The submitted implementation already reduces its lead pencils to **64/124 dimensions**, so large redundant layer groupings do not expose the intended missing rank-aware capability. At **1,568–1,600 lead orbitals**, the official reference's full-SVD workspace exceeds the 1-GiB address-space cap. Those two probes are **ineligible**, not participant failures. The reference cap was not relaxed and a new oracle was not invented to force retention.

No meaningful failure region survives. See `authoring/pilot03_counterexamples.md` and `private/reference/overgroup_probes/summary.json`.

## 6. Ratchets and confirmation

- **Scientific ratchets built: 0 of the allowed maximum 2 per concept.** Neither provisional finalist has a fair, reference-valid failure region on which to base one.
- **Fresh ratchet-confirmation model runs: 0. Final fresh confirmation scores: not applicable.** The protocol's counterexample gate rejects both concepts before that stage. Reserved initial confirmation files are not misrepresented as fresh-model confirmation results.
- Pilot02's author-only convention diagnostic is not a new fresh-agent score. Pilot03's extended scale probes are counterexample searches, not a new task or model trial.
- No fifth pilot, random edge-case accumulation, threshold tightening, hidden convention, or fabricated low score is used to force an accepted task.

## 7. Isolation and reproducibility

Fresh agents can access only their participant and attempt trees plus necessary runtime files. Evaluation separately uses bubblewrap with a scrubbed environment, no network/reference mounts, per-case resource limits and symlink/nonregular-output protections. `authoring/security_audit.json` confirms that private source, reference outputs and archived attempts are unreadable, while NumPy/BLAS and temporary outputs work; entrypoint/output symlink escapes are rejected.

Participant hashes for the valid runs are frozen in `authoring/tournament/initial/participant_hashes.json`. The final audit checks them again. Each pilot retains `participant/`, `private/` and `attempt/`; **do not mount the whole output directory into a participant session**. The private evaluators accept `--submission DIR --split test|challenge|confirmation --output REPORT.json`. Their authoring notes list reference-generation commands and exact dependencies. Run submitted evaluation with the necessary outer approval while retaining its inner sandbox; never treat an isolation failure as scientific failure.

## Final decision

**No accepted task.** This is an empirical rejection of the four built concepts under the requested model and validity rules—not a claim that the paper can never motivate a harder task. The demonstrated gaps are either solved, lack a fair public specification for the residual, or have no reference-valid harder region within the bounded search. Publishing one as frontier-hard would contradict the observed evidence.
