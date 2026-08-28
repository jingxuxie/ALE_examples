# Paper-derived task authoring report

## Status

The four permitted concepts have been built and attempted by isolated fresh `ultima-alpha` sessions. All four initial pilots are empirically solved, including every initial hidden family. A source-grounded largest-cell failure supports one focused geometry ratchet, whose independent fresh confirmation is running. All preregistered ratchet reference gates pass. No task is accepted yet.

The detailed candidate inventory is in `CANDIDATES.md`; the chronological evidence ledger is in `TOURNAMENT.md`; machine-readable initial results are in `tournament_results.json`. All paths below are relative to this directory.

## Source and solution-gap audit

The target is arXiv:1903.06168, *Enhanced proximity effect in zigzag-shaped Majorana Josephson junctions*. The paper, supplement, author repository, experimental scripts, stored computations, and repository history were inspected. The official repository was cloned with history, at inspected HEAD `012e1ad347959690b7d25597ef8f1af34c43ac8d`. The retrieved issues, pull-request, and release listings are empty; no nonexistent PR or release is presented as evidence.

Two especially useful privileged artifacts are the original 98,400-entry disorder archive and the later geometry-optimization archive accompanying arXiv:2205.05689 / SciPost Phys. 14, 047. The latter is Zenodo record 7266609 v2, created October 31, 2022; the paper was published March 23, 2023. Its ZIP SHA-256 is `a25b6218cd609d1f2f3fa399d98b117e4c0c100ccdb91799a8c35b7c4cbf33f6`. Geometry references are unmodified stored epoch-800 masks, not solutions invented during this benchmark run. Original optimizer code and optimized masks were never mounted into fresh-agent environments.

The original disorder archive contains 41 salts, 0–40, despite the supplement's statement of 40 realizations. The exact Cartesian indexing and the distinction between disorder-calibration and Hamiltonian masses are documented rather than silently reconciled. The source-side Hamiltonian/calibration replay agrees with the archive, and the independently developed fresh submission reproduces all selected outputs.

## Eight candidate directions

| Direction | Candidate gap | Existing privileged solution | Outcome |
|---|---|---|---|
| A: pre/post fix | Historical boundary and global-gap regressions | Actual later geometry and gap-return fixes | Built as 01 |
| B: adjacent improvement | Zigzag baseline to optimized fabricable contacts | Later greedy-optimization code and stored designs | Built as 04 |
| C: realistic scale | Clean workflow to calibrated disordered supercells | Official disorder implementation and 98,400 author outputs | Built as 02 |
| D: physical-family transfer | Two-contact workflow to single-contact / textured-field devices | Original supplemental implementation and calculations | Not selected; less independent than the selected branches |
| E: real-data discrepancy | Raw conductance versus instrument-calibrated conductance | Official TGP frequency/filter and bias-correction modules | Not selected; operational artifact verified after four slots were committed |
| F: integration | Orbital gauge phases across finite device and periodic leads | Later official magnetic-gauge implementation | Not selected; weaker direct tie to the target's model |
| G: ablation | Interface transparency versus geometric flight-length cutoff | Supplemental short-corrugation control | Not selected; narrow reference coverage and spectral overlap |
| H: correctness/performance | Finite-window fitting versus asymptotic/end-subspace localization | Official translation-mode and localization methods, stored states | Built as 03 |

`CANDIDATES.md` gives, for every candidate, the participant-visible start, private artifact, central outcome, generic shortcut, its expected failure regime, independent bottlenecks, and check. E is instrument calibration, not an assertion that disputed transport data provide definitive topological labels. No fifth pilot was built.

## Anti-compression and public artifacts

Before implementation the four designs were screened for more than one technical bottleneck: interacting geometry/spectral fixes (01); calibrated disorder plus large-scale global spectra (02); asymptotic modes plus finite-end subspace extraction (03); fabrication, topology, robust inverse design, and efficient full-scale evaluation (04). These were hypotheses, not declarations of hardness. Empirical compression to an adequate general solver is grounds for rejection.

Each initial pilot has `participant/TASK.md`, `participant/input/`, `participant/workspace/`, `private/reference/`, `private/challenge_pool/`, `private/evaluator.py`, and `attempt/`. Missions do not name the paper. Detailed interfaces and scientific conventions are public where needed for a well-posed task; hidden labels, optimized designs, and author implementations are not. Only minimal unlabeled examples are public. No large labeled development set was released.

## Isolation and execution

The supplied `run_allowlisted_codex.sh` was used, unmodified, with `--model ultima-alpha --effort high --task-read-only`. Each completed attempt starts from an empty writable attempt directory and has only its participant tree and own attempt as task-artifact access. The limit is 3600 seconds per fresh session. Network and approvals are disabled in those sessions. All four participant hashes remain unchanged.

Numerical grading separately uses a restricted filesystem sandbox. A probe successfully imports the numerical runtime while confirming that the source repository outside its mounts is invisible. The numerical solver sees staged requests and its own public/code trees, not reference files. Geometry claims are ignored: trusted code recomputes fabrication, spectra, and topology from returned masks.

An initial localization launch inherited an open stdin and was terminated after 464 seconds without a submission. That infrastructure record is retained separately and excluded from hardness scoring. The corrected launcher uses `/dev/null` for stdin. Author helpers performed bounded construction/research work; they are not counted as fresh pilots and never substitute for the requested model attempts.

## Initial tournament

| Concept | Fresh-session seconds | Reference core | Fresh mean core | Worst family | State |
|---|---:|---:|---:|---:|---|
| 01: revision repair | 859.01 | 1.000 | 1.000 | 1.000 | Solved; reject |
| 02: disorder ensemble | 1403.90 | 1.000, stored-output oracle | 1.000 | 1.000 | Solved; reject |
| 03: localization | 558.43 | 1.000 | 1.000 | 1.000 | Solved; reject |
| 04: geometry design | 3446.30 | 1.000 | 2.546104 | 1.015575 | Initial pilot solved; extended audit |

The first three are tied at numerical precision, not meaningfully ranked by floating-point differences from 1. All completed implementations are executable and scientifically complete in their tested scope. 02 and 04 receive the extended counterexample investigations because their realistic-scale and inverse-design bottlenecks are the strongest remaining hypotheses; this provisional choice is not an acceptance or a claim that the others have hidden substantive failures.

### Observed compression and correctness

- **01:** Direct repair of the actual boundary predicate and spectral-minimum return, followed by ordinary dense/sparse minimization, solves all 12 cases across three families. Hidden execution totals 174.09 seconds. This repair fixture is not claimed to be a realistic-scale spectral challenge.
- **02:** Deterministic disorder calibration plus reordered sparse shift-invert and adaptive momentum minimization solves all 18 cases, including scattering, phase-biased, and clean-like shifts. Initial/discovery/additional-holdout scores are all 1.000; the maximum absolute archive discrepancy is 6.45e-11 meV. Per-case times are 90.63–170.57 seconds under a 600-second limit; total execution is 2390.09 seconds. A single numerical strategy handles the entire intended pool.
- **03:** Rank-reduced generalized quadratic pencils solve the singular/grouped/gauge-transformed bulk cases. Small projected Hamiltonian/position eigensystems and the stated amplitude-density regression solve finite-end cases. All 13 bulk and five finite-end cases pass; total execution is 51.12 seconds. Long-coherence and basis-mixing cases do not defeat the completed implementation.
- **04:** The submitted implementation searches rounded/multiple-bend boundary graphs and adapts amplitude, width, harmonic content, and rounding. It uses reflection sectors, reordered sparse LU, momentum screening, and separate topology/robustness grids. Trusted scores are **5.539642** (doped-1300), **1.083096** (matched-1300), and **1.015575** (matched-980), all physically and geometrically feasible. Runs exit zero in 1114.80, 1135.03, and 1118.33 seconds respectively. Scores above one are deliberately not clipped. This is an implemented multicomponent optimizer with measured outcomes, not a result inferred from its README.

## Realistic-scale evidence and caveats

02 uses a full three-period 3900 nm cell with 124,800 BdG degrees of freedom. A dense allocation really fails under 12 GiB; one complex dense matrix alone requires 249,200,640,000 bytes. A straightforward source-side SciPy replay times out at 1500 seconds. A reordered author replay matches a grid eigenvalue to 4.70e-14 meV but exits during refinement on a residual guard, so it is **not** reported as a successful global-gap computation. Conversely, the completed fresh sparse solver succeeds rapidly; the author's incomplete replay cannot establish hardness or universal direct-method failure.

03 retains the source's 145,600-degree-of-freedom finite device and 4.55 micrometer scale, but the small supplied low-energy subspace admits efficient projection. Its large raw data size does not make that bottleneck hard.

04 uses actual 12,936–15,860-degree-of-freedom cells, not a coarse surrogate. Strong/weak gaps and class-D invariants are precomputed at 51 momenta and three operating points per family. The independent forward implementation reproduces a stored author gap to about 4e-17 meV. Per-request optimization is limited to 1200 wall seconds, two cores, 2400 CPU seconds, and 6 GiB.

A witnessed two-parameter direct-forward coordinate optimizer reaches normalized core **0.36926** on matched-1300 in 1200 seconds, completing six candidates and excluding a partial seventh. This demonstrates failure of that baseline, not all generic algorithms. A full-size NumPy dense eigensolver fails allocation under 6 GiB. A SciPy in-place dense call remains running at a 60-second watchdog; that alone does **not** establish failure at 1200 seconds. The reported 140-geometry grid cost is explicitly an extrapolation, not an executed benchmark. Full traces are under `pilots/04_geometry_design/private/reference/performance/`.

## Scoring and decision discipline

Accuracy pilots use continuous residual-based qualities relative to weak and strong anchors; raw errors and family scores are retained. Their pilot normalizations include a lower clamp, and 03 also caps improvement above its numerical strong anchor. Those are limitations for production use, not grounds for calling machine-precision solutions hard. Geometry uses the unbounded normalization `(R - R_weak) / (R_strong - R_weak)`, with `R = 0.5 * mean(gaps) + 0.5 * min(gaps)`. Scores above one are retained, and geometry/topology feasibility is separately mandatory. It is a **51-point sampled lattice gap**, not a certified continuum minimum.

No runtime, schema, dependency, incomplete reference calculation, or hidden sampling ambiguity is counted as a substantive unsolved component. Mean and worst-family performance are both required in the decision; a high-scoring family cannot erase a central failing branch. Ratchets must follow a demonstrated, source-grounded failure region and use new held-out cases. No random-edge-case or tolerance-only ratchet has been applied.

## Counterexample and confirmation status

01 and 03 have no substantive failures in their full intended pools and are not ratcheted. 02 also has no failures across its initial six, discovery six, and independent final-pool six cases. It is rejected rather than extended with more salts.

04's scout compares the original private reference with two additional, unmodified feasible published histories (`seed_1` and `zigzag`) on the official operating grid. The disconnected `no_mirror_sym` artifact is excluded without repair or relaxed fabrication constraints. The bounded first reference scout completes 11/18 measurements; incomplete values imply nothing. Improvements between author masks are not counterexamples to the participant. The public-example output passes all six full-resolution low-field/control probes and outperforms every completed eligible author comparison there. No pointwise maximum across different masks is treated as a realizable reference geometry.

The separate official 4-by-4 grid check of the actual scored matched-1300 mask reveals a **high-field performance tradeoff**. All 16 measurements complete and remain topological. At chemical potential 15 meV and Zeeman splitting 1.5 meV its gap is 0.115557 meV, versus the original archived design's 0.170488 meV; all four 1.5 meV points have smaller gaps than that reference. Nevertheless its full-grid mean/min robust gap is **0.149301** versus source **0.141590** meV. Thus the pointwise deficit is not automatically a failure of that aggregate objective.

The frozen executable is therefore retested on an explicitly specified high-field strip with newly chosen interior points. It adapts successfully: R=**0.228956** versus source **0.200079** meV, normalized score **1.230387**, complete feasibility, and 1128.37 seconds. This candidate counterexample is rejected as a missing-capability claim; the algorithm already handles the changed objective. Its private artifacts are under `pilots/04_geometry_design/private/highfield_research/`.

The largest published feasible cell is also audited separately: 1940 nm period, 66-by-97 sites, **25,608 BdG degrees of freedom**, the unchanged published epoch-800 design, and the same optimizer resource budget. This size is outside the frozen initial public range and is **not** scored as an initial failure. It exposes an actual next optimization gap: the frozen code finishes in **1146.22 seconds**, remains feasible, but attains R=**0.150397** versus weak **0.076664** and source **0.175688** meV, normalized **0.744592**. Its high-density gap is only 0.142940 versus source 0.225052 meV. Search refinement does not improve its best regional profile. The published 650 nm artifact fails the unchanged connected-contact condition and is not repaired or used; the 1620 nm artifact is feasible but is only inventoried. Files are under `pilots/04_geometry_design/private/scale_research/`.

### Ratchet 1 and independent confirmation

`pilots/04_geometry_design/ratchet_1/` focuses on improving the achieved large-cell layout. The working earlier optimizer and that layout are now a public baseline, while the original author geometry stays private. The physical model, fabrication rules, 51-momentum definition, topology checks and compute budget do not change. Exact operating points are now included in every request, removing undisclosed-sampling ambiguity. No error tolerance is tightened. The remaining discovery improvement is about **16.8% in robust physical gap**, not a last-bit numerical threshold.

Three new interior operating triples were fixed before calibration and confirmation; no case was dropped or resampled. They differ from the inspected discovery triple. All 18 baseline/source scenario measurements pass fabrication and Q=−1, and every source anchor improves robust R. Calibration takes 531.67 seconds; source core/worst are **1/1**, baseline **0/0**. The per-request baseline/source robust gaps are:

| Held-out request | Public baseline R (meV) | Existing source R (meV) |
|---|---:|---:|
| lower_offset | 0.157470428 | 0.181231138 |
| central_offset | 0.144502853 | 0.185551462 |
| high_density | 0.134079058 | 0.167989097 |

A full-size dense matrix allocation is also actually attempted under 6 GiB and fails: the matrix alone needs **10,492,314,624 bytes** (9.77 GiB). This complements, rather than replaces, the completed optimization failure. The ratchet rationale and preregistration are in `pilots/04_geometry_design/ratchet_1/private/RATCHET.md` and `pilots/04_geometry_design/ratchet_1/private/reference/source_manifest.json`.

An independent empty-attempt, read-only-participant `ultima-alpha` confirmation is running. It has no previous attempt history or private source access; only the explicitly published baseline carries forward. Reference calibration overlaps the early confirmation period, using already frozen cases and masks. No cases or public files change after launch. This is the same user-requested model alias in a fresh session, not evidence of cross-model-family robustness. Acceptance remains conditional on the requested score/completeness/substantive-failure gates.

## Reproduction entry points

- `author_tools/launch_pilot.py`: isolated one-hour fresh sessions and hash/termination records.
- `author_tools/sandbox_solver.py`: private-data isolation for numerical submissions.
- `author_tools/grade_geometry.py`: resource-limited geometry execution followed by trusted scoring.
- Each `pilots/*/private/evaluator.py`: core evaluation and reference/calibration checks; use `--help` for its exact interface.
- `author_tools/summarize.py`: regenerate the machine-readable initial tournament ledger.
- `pilots/*/private/runs/initial/`: full model transcripts, launch records, executable-submission scores, and available runtime records.
- `pilots/04_geometry_design/private/counterexample_research/`: source grid, feasible-mask provenance, full spectral probes, and comparison records.

Only an accepted concept will be promoted to a production task. Rejected pilots remain as evidence, not as a falsely certified frontier-hard benchmark.
