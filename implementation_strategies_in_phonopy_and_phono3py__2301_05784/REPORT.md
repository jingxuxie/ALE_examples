# Final report: no task accepted

**Decision: REJECTED.** None of the four tested concepts meets the requested
frontier-hard retention gates. All four fresh `ultima-alpha` submissions solve
their valid initial cases robustly. Source-grounded larger-scale searches also
fail to expose a genuine solution gap that the submissions cannot bridge.

This is a negative result for this four-concept tournament, not a claim that
the paper cannot support any other hard task. No solved concept is promoted
to an accepted benchmark, and no apparent failure caused by an invalid oracle
is counted as hardness.

Audit date: August 28, 2026 UTC / August 27, 2026 America/Los_Angeles.

## 1. Scope and source mining

Target: *Implementation strategies in phonopy and phono3py*, arXiv:2301.05784.
The paper, including its appendices, three official repository histories,
release notes, concrete fixes/PRs, later methods, and official experiment/test
data were inspected. Exact revisions, package versions and hashes are retained
in `author/provenance.json` and `author/SOURCE_AUDIT.md`.

Eight distinct candidate directions were recorded **before construction**:

| Direction | Candidate gap | Pilot? |
|---|---|---|
| A: pre/post behavior | Single-origin versus three-origin cubic interpolation | cubic |
| B: adjacent improvement | Symmetry-constrained joint harmonic/cubic force fitting | fitting |
| C: realistic scale | Generalized BZ geometry plus tetrahedron integration | grid |
| D: physical-family transfer | Coherent Wigner transport in complex crystals | no |
| E: model discrepancy | Temperature-renormalized unstable phonons / SSCHA | no |
| F: integration | Different harmonic and cubic supercells/solver paths | no separate pilot |
| G: ablation correctness | Isotope-scattering normalization and channel ablations | no |
| H: correctness/performance | Analytic polar dynamical derivatives and mode response | polar |

`author/CANDIDATES.md` contains, for every direction, the participant starting
artifact, private solution artifact, central outcome, prospective shortcut,
failure mechanism, independent bottlenecks and proposed checks. Checks and
shortcut limitations for unbuilt candidates are proposals, not empirical results.
Unbuilt directions were not declared easy without testing.

The public starters are explicitly restricted author adapters/ablations. They
are not misrepresented as byte-for-byte historical checkouts. Official solution
modules, basis sets, targets and native heldout forces stay private. TASK files
do not mention the paper and contain 137–179 words; detailed API conventions
reside in workspace contracts. Each pilot exposes one unlabeled smoke input,
not a labeled development set sampled from its private generator.

## 2. Four pilots and private references

| Pilot | Independent core outcomes | Privileged reference | Initial private cases |
|---|---|---|---|
| fitting | Harmonic/cubic reconstruction, physical predictions and simultaneous invariances | symfc 1.5.4 official bases/solvers; rank-aware Si correction cross-checked with 1.7.3 | 6, four physical families; up to 512 harmonic / 128 cubic atoms |
| cubic | Complex three-origin amplitude and mode coupling | Explicitly enabled phono3py 3.19.2 C kernels | 12; NaCl, AlN, Si; full/compact 64/72-atom cells |
| grid | Integer/BZ geometry and tetrahedron spectral measure | phono3py 3.19.2 / phonopy 2.43.4, with independent geometry and 4.1.0 backend checks | 10; skew, exact ties, flat/close branches, 105,600/110,592-point grids |
| polar | Polar derivative and independently supplied degenerate-mode response packets | phonopy 4.1.0 Python/Rust analytic implementation | 12; NaCl, SnO2, TiO2; oblique frames, near-Gamma and degenerate subspaces |

Anti-compression decisions were recorded before builds. The subsequent empirical
results show that the initial two-bottleneck specifications nevertheless remain
compressible into successful general implementations. The cubic pilot is a
correctness pilot on realistic supercells, not evidence of a transport-scale
runtime barrier. The stronger scale tests are described below.

Independent reference evidence is under each `private/reference/` directory.
Cubic direct kernels agree with monolithic interaction results to 2.31e-15.
Grid references pass independent closest-image/simplex checks and selected
Python/C/Rust cross-checks. Polar Python/Rust derivatives and independent mode
response checks pass. Fitting references include native-force and invariance
checks; the initial Si exception is explicitly corrected in Section 5.
Stored-reference self-checks are labeled as such and are not substituted for
these independent validations or reported as runtime measurements.

## 3. Actual fresh-agent tournament

Four isolated, ephemeral `ultima-alpha` attempts used the supplied unmodified
`run_allowlisted_codex.sh`, `--effort high`, read-only participants and initially
empty attempt folders. Each had a 3,600-second limit and returned before it.
No previous attempt, private source, target or challenge-pool directory was
allowlisted. Public hashes remained unchanged. The evaluator separately
isolates the submission, public assets, a single unlabeled input and output,
with network/PID namespaces and per-process limits.

| Pilot | Model seconds | Core mean | Worst family | Worst family-component | Completed |
|---|---:|---:|---:|---:|---:|
| fitting, corrected oracle | 1030.50 | **0.997303** | **0.994588** | 0.991950 | 6/6 |
| cubic | 631.24 | **1.000000** | **1.000000** | 1.000000 | 12/12 |
| grid | 1095.69 | **1.000000** | **1.000000** | 1.000000 | 10/10 |
| polar | 798.66 | **1.000000** | **1.000000** | 1.000000 | 12/12 |

“1.000000” is rounded, not a saturation threshold. Raw scores/errors are stored
in `author/scores/`. The corresponding validated references score above 0.90;
the corrected fitting reference is approximately 0.9973 because its core also
includes irreducible error against actual heldout forces. Cubic/grid references
score 1.0, and the independently recomputed polar reference approximately 1.0.

The original fitting report was 0.911127 overall / 0.478223 worst family. That
severe family failure was investigated rather than averaged away. It was a
reference error, not a participant error; the corrected row is authoritative.
Both reports and all original reference artifacts remain available.

Initial evaluation totals / largest measured RSS were: fitting corrected
9.02 s / 221,232 KiB; cubic 200.50 s / 115,644 KiB across 12 cases; grid
28.50 s / 130,960 KiB; polar 67.90 s / 39,852 KiB. These totals include sandbox
overhead and are single-run observations under shared-host load, not controlled
speedup estimates. The resource caps apply per case, not to these totals.

Four preliminary launcher processes waited on inherited stdin before model
execution. They were stopped, preserved in `author/pilot_logs_stdin_blocked/`,
and restarted with stdin closed. They produced no submissions and are not
scored model attempts. The supplied allowlist runner itself was not modified.

## 4. General solutions actually discovered

- **Fitting:** sparse orbit-local invariant tensor bases, acoustic nullspaces,
  blocked feature construction, sufficient statistics for well-conditioned
  fits and SVD for rank-deficient fits. The same implementation handles joint
  and different-supercell conditional objectives and all tested crystal families.
- **Cubic:** multiplicity-aware complex phases, three-origin amplitude averaging
  and tensor contractions for mode strengths. No natural accuracy failure was
  found in the full/compact, noncommensurate and nonzero-reciprocal-sum cases.
- **Grid:** integer quotient keys, lattice reduction and radius-bounded closest
  image enumeration; analytic tetrahedron polynomials accumulated on a threshold
  interval tree. It handles repeated energies and point masses without smearing
  or a tetrahedron-by-threshold dense array.
- **Polar:** analytic short-/long-range derivatives and Hermitian degenerate
  perturbation operators with the specified coordinate and gauge conventions.
  A separate author audit also found that a simple smaller finite-difference
  step nearly solves the derivative branch, but not the independent response
  branch; that audit is not confused with the complete submitted solution.

These are observed submitted methods, not predictions that a standard solver
might work. Submitted implementation/testing claims are consistent with the
valid private results. Their own synthetic tests are not relabeled as private
or native-material tests.

## 5. Invalid reference and scoring shortcuts

### Rank-deficient Si oracle

The Si joint design has shape 2304-by-17 and rank 16. The initial high-level
normal-equation oracle is unsuitable for the public minimum-norm objective.
Both installed symfc versions reproduce it, but explicit SVD in the official
invariant basis agrees with the participant. The stored reference has training
SSE 646.3433 and heldout RMSE 0.558679; the participant and independent rank-aware
fit have SSE 0.1812266 and heldout RMSE 0.007047. A feasible descent direction
has objective derivative -1292.324, disproving the old target's optimality.

No participant code or input was changed. A separate corrected manifest and
target are used for rescoring. This is a gold correction, **not a ratchet or
another model attempt**. See `author/SI_ORACLE_CORRECTION.md` and `author/si_audit/`.

### Calibration weaknesses

The independent direct-scoring audit found:

- Generic zero fitting tensors score 0.754598 on the original six cases and
  0.728835 on the heldout subset even without Si. Homogeneous constraints reward
  zeros indirectly because their errors are normalized by a poor unconstrained
  baseline. These are not successful scientific fits.
- A **privileged diagnostic** using reference fc2 with zero fc3 scores 0.920109.
  This is an ablation exposing inadequate cubic discrimination, not a generic
  solver or a claim that a participant has the reference harmonic tensor.
- Grid's flat-case calibration can award 0.999944 to missing CDF/wrong images on
  one heldout case. That shortcut scores only 0.446337 overall; it is a local
  calibration defect, not a universal grid solution.
- Polar's documented scientific floors make its actual starter mean 0.623900,
  not exactly 0.5. Floors were established before the pilot; negligible errors
  were not amplified merely because the starter was already accurate.

These findings prevent treating the raw screening thresholds as sufficient
acceptance evidence. No scale was tightened after seeing a submission. Because
every valid submission actually solves the science, score repairs would not
produce a defensible hard candidate. The rejected prototype scorers and their
known limitations are preserved for audit, not shipped as production graders.
See `author/CONTRACT_AUDIT.md` for 126 recorded direct-score checks.

## 6. Counterexample-guided searches on two concepts

Fitting and grid received the two bounded follow-up searches. After the Si
correction all initial pilots lie in the solved tier; roundoff differences
among scores near one were not treated as substantive ranking differences.
The two scale-sensitive concepts were the useful remaining search targets.

### Longer-range force fitting

The same submitted solver was tested on three new native-observation cases.
The source-grounded change is longer-range cubic support and substantially
larger invariant spaces, not extra arbitrary rows or tighter tolerances.

| Challenge | Cubic parameters | Solver seconds | Peak KiB | Relative cubic error |
|---|---:|---:|---:|---:|
| NaCl, 512/64 atoms, full cubic support | 758 | 12.91 | 221,420 | 7.38e-15 |
| GaN128, 5.5 Angstrom | 1,859 | 10.97 | 623,772 | 1.21e-8 |
| SnO272, 5.5 Angstrom | 3,217 | 32.96 | 830,148 | 5.64e-13 |

References satisfy full-rank, independently contracted stationarity, symmetry,
support and native-force checks within the unchanged 180 s / 8 GiB cap. Maximum
submitted-versus-native heldout prediction disagreement is 1.75e-10 eV/Angstrom.
Longer-range GaN improves heldout RMSE by about 26%, confirming scientific
relevance, yet the submitted solver still succeeds. Increasing the range of
NaCl/SnO2 did not improve heldout error on these splits; further inflation just
to seek failure would not be justified by that evidence.

A separate explicit dense-projector allocation needs 391,378,894,848 bytes and
fails an 8-GiB limit. This rules out that particular dense baseline, **not** the
successful general sparse/orbit implementation. It does not establish hardness.

Evidence: `concepts/fitting/private/reference/counterexamples/REPORT.md` and the
separate `counterexamples_manifest.json`.

### Larger grids and physical-family shifts

Four new challenges cover AlN on **1,048,576 points / all 12 branches**, oblique
TiO2, long-wave SnO2 with many close branches, and **42-branch Zr3N4**. The TiO2
representation has basis condition about 759; closest-image sets and order
still match exactly. The expanded mean core is **0.9999999999999946**; spectral
errors remain at roundoff.

The million-point submission takes 11.09 s and peaks at 991,748 KiB; the official
oracle takes 85.89 s. All references and submissions pass the same 180 s / 8 GiB
limits. These are measured times for their recorded execution scopes, not a
claim that all implementations or machines have that speed ratio.

Evidence: `concepts/grid/private/reference/bounded_search_01/README.md`,
`summary.json` and `manifest_search_01.json`. Original artifacts remain unchanged.

## 7. Ratchets, second-model gate and final decision

**No genuine failure region survives either search.** The Si region is an
invalid-oracle region; it cannot justify a ratchet. Larger valid fitting and
grid regions are solved. Cubic and polar are already solved across their
private families with complete implementations.

- Concepts built: **4 / maximum 4**.
- Valid initial fresh attempts: **4**, all `ultima-alpha`, each below one hour.
- Follow-up counterexample searches: **2 concepts**, one bounded pass each.
- Ratcheted task versions built: **0**; no source-grounded failure justified one.
- Second-model/fresh-ratchet attempts: **0, inapplicable after rejection**.
- Final confirmation **of hardness**: none. Expanded checks above replay the
  unchanged initial submissions; they are not mislabeled as fresh-model tests.
- Accepted task: **none**. Every valid fresh score is above 0.90, not below 0.70,
  and no central scientific component remains unsolved in validated regimes.

Launching another agent on an unchanged solved task, adding arbitrary edge cases,
or tightening thresholds would not satisfy the requested counterexample-guided
ratchet rule. No such artificial ratchet was made. No accepted participant/private
production package is published at the root; all four remain audit prototypes.

## 8. Reproducibility and artifact map

- `STATUS.json`: machine-readable rejection and score index.
- `author/CANDIDATES.md`, `SOURCE_AUDIT.md`, `provenance.json`: mining and pins.
- `author/preflight.json`, `isolation_probe/report.json`: interface/separation checks.
- `author/pilot_logs/`: actual model logs, commands, times and immutable hashes.
- `author/scores/`: per-case components, family minima, errors, runtime and RSS.
- `concepts/*/participant/`: exactly the frozen public tasks seen by fresh agents.
- `concepts/*/attempt/`: actual submitted programs, tests and claims.
- `concepts/*/private/`: references, challenge pools, evaluators and source audits.

Use `author/score_submission.py` to replay an archived submission through the
isolated evaluator. For fitting, explicitly pass
`--manifest concepts/fitting/private/challenge_pool/manifest_corrected.json`;
the original default manifest is preserved only to reproduce the invalid initial
Si result. Per-concept READMEs document reference construction and follow-up
search commands. Evaluator bubblewrap may require launch outside an outer
sandbox; its own narrow mounts/network isolation remain enabled.
