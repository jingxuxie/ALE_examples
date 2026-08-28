# Empirical tournament ledger

This ledger is provisional until all initial and retained-concept confirmation runs finish. A low number caused by an infrastructure failure is not counted as evidence of scientific difficulty.

## Isolation and execution

The supplied `run_allowlisted_codex.sh` is used without modification, with `--model ultima-alpha --effort high --task-read-only`. Each invocation receives only its participant tree and an initially empty attempt tree, plus the runner's minimal system/runtime mounts. The launch limit is 3600 seconds. The parent launcher records commands, hashes before/after, return status, and elapsed time. Public files are checked for changes.

Evaluation uses a separate verified filesystem sandbox. Its probe successfully imported NumPy/SciPy and could not read the official source repository outside its mounts. Only staged problem inputs, the submitted solver tree, and the public task are mounted for numerical submissions. Reference files are not mounted. Geometry scores are computed afterward by trusted author-side code from submitted masks, not participant claims.

A preliminary localization launcher inherited an open stdin and was terminated after 464 seconds. Its transcript and termination metadata are retained under `initial_stdin_infrastructure_issue`. It produced no submission and is excluded from scientific scoring. The corrected launcher explicitly uses `/dev/null` for stdin; the completed localization run below starts from an empty attempt directory. The initial console message alone is not a reliable progress indicator; subsequent process inspection and completed transcripts confirm actual solver work.

## Completed initial outcomes

| Concept | Reference | Fresh core | Worst family | Solver runtime | Decision |
|---|---:|---:|---:|---:|---|
| 01 — Revision repair | 1.000 | 1.000 | 1.000 | 174.09 s including isolation | Reject: robustly solved |
| 02 — Disorder ensemble | 1.000 stored reference | 1.000 | 1.000 | 843.50 s for six initial cases | Reject: all 18 pool cases solved |
| 03 — Localization | 1.000 | 1.000 | 1.000 | 51.12 s including isolation | Reject: robustly solved |
| 04 — Geometry design | 1.000 | 2.546104 | 1.015575 | 1114.80–1135.03 s per request | Initial pilot solved; source-grounded audits pending |

Revision repair's fresh session completed in 859.01 seconds. All 12 hidden cases pass across finite boundaries, wrapped boundaries, and interior-momentum gaps. Boundary responses are exact; spectral errors are at most approximately 1.2e-9 meV. The implementation repairs the historical boundary predicate and computes/refines the actual spectral minimum. No unsolved interacting fault remains in the intended pool. Increasing a small repair fixture to an unrelated giant spectral calculation would change the bottleneck rather than reveal a genuine remaining repair failure, so no ratchet is applied.

Localization's fresh session completed in 558.43 seconds. All 18 hidden cases pass: 13 bulk-tail cases and five finite-end cases. Raw family qualities are 0.999999999941 and essentially 1.0. The participant implements SVD rank reduction plus a generalized quadratic pencil for bulk decay, and small projected-Hamiltonian/position eigensystems plus the specified density regression for finite ends. It explicitly handles singular hoppings, grouped unit cells, gauge transformations, and basis rotations. These are substantive correct solutions, not output memorization.

The full hidden pool already contains the source-grounded long-coherence, parameter-shifted, singular/grouped, and mixed-basis regions. No failing region was found there. Merely adding more gauge transformations or matrix sizes would not create a new scientific bottleneck, so this concept is not ratcheted.

Disorder's fresh session completed in 1403.90 seconds. Its independently implemented deterministic disorder calibration and reordered sparse shift-invert solver reproduce all six initial cases, all six discovery cases, and all six additional pool holdouts. Scores are 1.000 in every split and family to displayed precision. The last pool split has mean 0.9999999999999994 and worst family 0.999999999999998; the maximum observed absolute gap discrepancy across the 18 cases is on the order of 1e-10 meV, not a material physical failure. Discovery and final-pool execution take 797.87 and 748.72 seconds respectively. These are the same frozen submission, not extra fresh-agent attempts. No source-grounded failure region is found, so increasing random seeds or tightening tolerances would not justify a ratchet.

## Reference/resource issues under audit

02 has 98,400 stored author calculations with an explicit index mapping and archive hash. The actual archive uses salts 0–40 (41 realizations), although the supplement says 40. This discrepancy is documented rather than silently changed. Strong stored-output and zero-baseline scoring checks give 1 and 0, but those checks alone do not validate a numerical implementation.

An independent 124,800-degree-of-freedom replay with the straightforward SciPy fallback hit a 1500-second limit before producing its full momentum minimum. This initially left the reference/resource gate unresolved. The subsequent checks and completed fresh submission described here resolve the scientific comparison, but do not turn that incomplete author replay into an executable success. Its timeout is evidence about that direct workflow, not a fresh-agent hardness score.

Subsequent source-side checks prove exact agreement of the full Hamiltonian and disorder calibration at three phases. An optimized low-pivot MMD replay evaluates all 31 original grid points and obtains an eigenvalue within 4.70e-14 meV of the archive, but its local refinement exits on a conservative residual guard; this is not a completed global-gap certificate. The fresh participant independently completes the first scored case in 146.17 seconds and matches the archive. Thus a blanket claim that generic sparse direct methods fail at this scale would be false. The incomplete author replay is not used to inflate difficulty. Details are in `pilots/02_disorder_ensemble/private/reference/RESOURCE_GATE.md`.

The dense baseline was actually subjected to the 12 GiB address-space limit and failed even to allocate one 124,800-square complex Hamiltonian. That matrix alone needs 249,200,640,000 bytes, before eigenvectors/workspace. This is a full physical cell, not a scaled toy system.

04 uses the published follow-up archive's optimized masks privately and the original unoptimized zigzag publicly. The independent forward model reproduces a stored author gap to approximately 4e-17 meV at 15,860 degrees of freedom, including a nontrivial class-D invariant. All three weak/strong family calibrations are ready, with weak normalized score 0 and strong 1. Actual new submissions still require independent geometry, topology, and robustness evaluation.

That independent initial evaluation is now complete: doped-1300 scores 5.539642, matched-1300 1.083096, and matched-980 1.015575; all fabrication and topology gates pass, and every executable invocation exits zero inside 1200 seconds. Strong performance in the doped family is not allowed to hide another failure: the worst family also exceeds one. The source-grid audit nevertheless finds a real upper-field gap deficit in the broad-region output. An explicitly retargeted high-field invocation and the largest published feasible cell are being tested before deciding whether this is a genuine solver gap. These are frozen-code numerical audits, not additional fresh models or a fifth concept.

## Resolved audits and first ratchet

The high-field adaptation test completes at score **1.230387**, with R=0.228956 versus source 0.200079 meV. It exits zero in 1128.37 seconds and passes all constraints. Thus the earlier pointwise deficit is not used to fabricate a hard task: the unchanged executable already adapts to an explicit change of objective. On the full official 16-point grid, the earlier broad output also has better aggregate R than the reference, despite its eight pointwise deficits.

The 1940 nm published cell does expose an optimization gap. The frozen executable completes in 1146.22 seconds, all constraints pass, and R=0.150397 versus original weak 0.076664 and source 0.175688 meV: **0.744592**. The deficient middle/high-density gaps and lack of refinement progress are substantive, not an execution failure. This is an out-of-initial-size-range diagnostic, not a retroactive change to the initial scores.

Ratchet 1 therefore focuses on that largest-cell gap and publishes the achieved geometry plus the working old optimizer as a baseline. Exact scored operating points are supplied in every request; physical/numerical/fabrication definitions and compute limits stay unchanged. Three new preregistered operating triples are calibrated without dropping or resampling any case. All 18 weak/strong scenario evaluations pass; baseline scores 0/0 and source 1/1 (core/worst). A fresh, isolated one-hour `ultima-alpha` confirmation is running. No source optimizer, prior attempt history, or private reference is exposed; only the explicitly promoted baseline carries forward.
