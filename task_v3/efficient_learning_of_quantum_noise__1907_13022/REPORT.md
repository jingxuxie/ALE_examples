# Decision: no qualifying hard task within the four-concept budget

**Reject all four built concepts. No production task is accepted.** Three are
robustly solved by genuine isolated `ultima-alpha` attempts, including fresh
source-grounded challenge regions. The fourth has a low numerical score but an
ambiguous experimental oracle. Accepting it would reward guessing a private
fitting convention rather than establish an unsolved scientific capability.
This is a bounded empirical conclusion, not a claim that the paper or its
application domain contains no hard problems.

Research and runs occurred on August 27, 2026 (America/Los_Angeles), with final
evidence recorded on August 28, 2026 UTC. Four concepts and four initial model
attempts were used. Each had a 3,600-second ceiling; none timed out. Ratchet
counts are **0/2 per concept**. Second-model confirmation is **not applicable**:
no scientifically valid failure region qualified for a ratchet.

## 1. All candidate directions

`private/CANDIDATES.md` records the participant start, private solution,
outcome, shortcut, failure regime, independent bottlenecks and success check
for every candidate.

| Direction | Solution gap / privileged artifact | Disposition |
|---|---|---|
| A: pre-fix/post-fix | Actual unequal-cardinality CMI indexing correction in Juqst `08101ff`, with later tests | Mined; reference-regression audit, not an actual pre-fix-checkout pilot |
| B: adjacent improvement | Full arbitrary-weight sparse Pauli recovery; later sparse-reconstruction implementation | Built as concept 01 |
| C: realistic scale | Local observations to normalized global queries at about 100 qubits; precomputed contractions | Built as concept 04; synthetic source-grounded reference has lower artifact priority |
| D: physical-family transfer | Calibration-to-syndrome-preparation transfer in the 39-qubit follow-up | Not built: author-only code/data unavailable; paper summaries are not an executable oracle |
| E: real-data discrepancy | Correlated-noise reconstruction on official IBM 14-qubit acquisitions; withheld official analysis module | Built as concept 03; rejected for target ambiguity |
| F: integration | Self-consistent gate-set noise, SPAM, gauge and learnability; later PauliGST implementation | Built as concept 02 |
| G: missing ablation | Pairwise versus higher-order structure; official full distributions and higher-order analysis | Mined and partly exercised by concept 03; not an overlapping fifth pilot |
| H: performance/correctness | Significant-error population recovery with supported heralded failures; PauliPopRec implementation | Reserve distinct direction; not rejected on predicted ease and not built beyond the four-concept limit |

Inspected evidence includes the paper and supplement, official code/data and
experiment scripts, local repository history and tags, scientific fixes and
recorded pull requests, and adjacent papers. The archived target is the
**23-page v2 manuscript including its supplement**, stamped April 16, 2021.
The 2020 sparse work is later than the original 2019 preprint, not later than
v2. V2 already links reconstruction notebooks; no false request-only historical
gap is claimed.

Issue/release retrieval yielded no useful additional content; a GitHub API
archival request returned HTTP 403. The 39-qubit author-only data were not
obtained. `private/RESEARCH_AUDIT.md` discloses these limitations, and
`private/sources_manifest.json` pins repository commits and PDF hashes.

## 2. Four minimal pilots and anti-compression gates

Each pilot has the requested `participant/{TASK.md,input,workspace}`,
`private/{reference,challenge_pool,evaluator.py}` and `attempt` layout. Missions
are concise, omit the paper name and keep I/O specifications separate. No
hidden reference outputs, solution-bearing sources or large labeled
development sets are public. No production task was promoted.

- **01 Sparse:** 40–100 physical qubits, arbitrary-weight errors, collisions,
  dynamic range and approximate sparsity. Low-weight enumeration is invalid;
  dense storage needs `8 * 4**n` bytes. Support recovery, noise-aware decoding
  and probability estimation are distinct inspected requirements.
- **02 Gate-set:** connected 20-qubit core and 20/24-qubit challenge systems,
  up to 672 parameters and 6,048 rooted experiments. Signed Clifford
  propagation, structural/calibration identifiability and held-out physical
  prediction are separately required. The regression design is not supplied.
- **03 Experiment:** real 14-qubit acquisitions, mixed twirls, depth dependence,
  constrained reconstruction and correlation/conditional-information outputs.
  Twelve core and eight challenge windows derive from only **four real
  acquisitions**, not twenty independent experiments. The purported multiple
  outcomes ultimately depend too strongly on one ambiguous estimator.
- **04 Graphical:** up to 120 variables, degree-three interactions and bounded
  treewidth, with tilted weight, parity and pinned-event log probabilities.
  Factor inference and stable contraction are distinct steps, but exact
  positive blanket marginals expose a general conditional-logit shortcut.

The initial anti-compression gates rely on realistic scale and multiple
technical steps, not presumed hardness. Weak baselines were actually executed.
Large references were precomputed and checked against independent physical or
small exhaustive calculations. Infeasible dense 100-qubit allocation was not
attempted; its resource lower bound rules it out. The runnable weak baselines
provide the empirical comparison, without pretending to benchmark an
impossible allocation.

## 3. Isolated tournament and ranking

All attempts used the supplied allowlisted runner, `ultima-alpha`, `xhigh`
effort, no web search and empty attempt directories. Model headers, times,
participant hashes and frozen submission hashes are in `private/runs/pilot`.
Models had participant read access and attempt write access, plus required
runtime files—not other concepts, labels, references or earlier attempts.
Numerical evaluation separately stages one input and the solver under
Landlock; both filesystem aliases were tested in `private/isolation_audit.json`.

| Concept | Strong core | Weak core | Agent core | Worst core family | Challenge | Worst challenge family | Agent minutes |
|---|---:|---:|---:|---:|---:|---:|---:|
| 01 Sparse | 0.991460 | 0.008560 | 0.991404 | 0.974728 | 0.991298 | 0.974427 | 51.92 |
| 02 Gate-set | 0.991650 | 0.222999 | 0.991637 | 0.983136 | 0.992228 | 0.980083 | 48.55 |
| 03 Experiment | 1.000000* | 0.117690 | 0.415322 | 0.345570 | 0.267590 | 0.227702 | 30.23 |
| 04 Graphical | 1.000000 | 0.201525 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 12.59 |

`*` Experimental reference one means self-agreement with a pinned fitting
policy, not accuracy against a known latent physical channel.

There are 39 core and 26 challenge cases. Every model returns a substantive,
complete solver; no clerical execution failure establishes hardness. Public
files remain unchanged. The sole in-flight grader amendment hardened
experimental NPZ/output handling before grading without changing science,
targets, public files or losses. Its timing/hashes are in
`private/GRADER_AUDIT.md`. A placeholder preflight rejection preceded the sparse
model launch and is not an extra attempt.

Ranking by worst hidden family puts **experiment, sparse, gate-set, graphical**
in that order; overall scores agree. Experiment and sparse receive the primary
validity/counterexample screen. After experiment fails oracle validity,
gate-set is audited as the remaining valid backup. Graphical also receives an
independent fresh-region check rather than rejection by predicted ease.

## 4. Counterexamples and universal solvers

### Sparse: robustly solved

Support F1 is one on every original core/challenge case. Twelve predefined
fresh cases vary load, sign noise, 100-qubit dynamic range, nearly equal
collision amplitudes, physical background mass and heteroscedasticity. All
references pass score >0.9, F1 >=0.98 and raw loss <0.1; no cases are excluded or
reseeded after results. Frozen mean is **0.993307**, minimum case **0.962838**,
and all **3,752** significant labels are recovered. Maximum score deficit is
only 0.000234.

Three additional 100-qubit coded-index probes use the follow-up's linear-code
branch and an existing privately compiled BCH decoder. The original typical
row-count case and two exploratory O(n)-row extensions are clearly separated.
Reference and frozen solver recover all **576** significant labels. Frozen
scores are **0.994096, 0.994584, 0.993830**, maximum runtime **3.53 seconds**.
The solver already performs reliability-ordered linear-code decoding from
the offset matrix, not merely hard systematic signs; BCH checks do not defeat
it. This audit is not a fifth concept or a ratchet.

The generic solution combines sparse decoding, collision resolution and joint
refinement. It is not a lookup exploit. No omitted central capability remains
in the tested source-grounded regions. See
`concept_01_sparse/private/reference/counterexample_audit/REPORT.md` and
`private/coded_probe/REPORT.md`.

### Gate-set: robustly solved

Nine fresh 20/24-qubit cases alter calibration sectors, connected crosstalk,
compiled asymmetric-SPAM circuits and shot allocation. All qualify under
absolute reference and information-content checks. Frozen mean is
**0.998093**, worst family **0.997121**, worst case **0.996416**; there are
**zero errors in 2,016 identifiability decisions**. Maximum case-score
difference from reference is 0.000003758.

Frozen maximum runtime/RSS is **2.93 seconds / 96.44 MiB**, versus **33.78
seconds / 420.63 MiB** for the reference, inside the original 120-second /
3-GiB limit. Reference query/prediction improvements over weak baselines are
hundreds-fold; these are not uninformative-zero examples. Genuine signed
Clifford propagation, gauge/calibration linear algebra and positive-rate
fitting work generically across branches. See
`concept_02_gateset/private/reference/counterexample_audit/VERDICT.md`.

### Experiment: counterexample to the hardness interpretation

Pinned Juqst uses `17 * first / 64` and includes the first crossing point;
the paper describes `(first + 1/16) / 4` and discards crossing/later points.
Neither private fitting policy is specified publicly. Agreement with one
cannot establish that another defensible estimator is scientifically wrong.

On four full acquisitions, oracle-score means are **0.761903** for the literal
paper policy, **0.699194** for bounded full-range fitting and **0.803043** for a
late-weighted alternative. Full-range fitting is within **0.173%** of raw
held-out reference RMSE and **0.743%** of projected RMSE while improving
interior-depth prediction on every acquisition. Thus even a score below the
0.70 screening threshold need not indicate an unsolved component.

The submitted estimator is not uniformly better: mixed-acquisition interior
RMSE is 43–54% worse and low-order RMSE 18–33% worse. Its diagnostics are
nevertheless internally correct to **2.48e-15** given its channel. Four score
components do not imply four independent failures. Synthetic tests validate
the numerical port, not the true real-device channel. Revealing a private
cutoff would be a clerical policy-reproduction ratchet, not the frontier task
requested. See `concept_03_experiment/private/reference/policy_audit/REPORT.md`.

### Graphical: exact local data expose a shortcut

Six fresh 100–120-variable cases span all three families. Frozen mean/worst
family remain one to displayed precision; maximum log error is **1.82e-12**
and maximum runtime **0.70 seconds**. Three separate small exhaustive checks
validate the oracle. Conditional log-odds of exact blanket marginals directly
expose factor coefficients; log-domain elimination then handles global
queries. CMI structure search is unnecessary. New seeds, parity masks and
activities do not defeat the implemented general method. See
`concept_04_graphical/private/reference/counterexample_audit/REPORT.md`.

## 5. Scoring, ratchets and final screening

Scores are continuous and relative to executed weak baselines and strong
references. Sparse scoring combines uncapped nonidentity L1, support F1 and
independent spectral error with rational calibration. Gate-set separately
scores identifiability, invariant estimates and held-out means. Experimental
distribution/correlation/CMI/DAG errors and graphical event-log errors remain
visible rather than being obscured by an average. JSON retains family means,
worst-family scores, raw losses, runtime and applicable memory measurements.

The audits require absolute reference quality and informative physically valid
cases in addition to calibrated scores. They do not manufacture hardness by
renormalizing an inadequate reference. The experimental audit specifically
shows why reference-relative scoring alone is insufficient.

**Ratcheted concepts: none. Ratchet changes: none. New confirmation attempts:
none. Final confirmation scores: N/A, not zero and not estimated.** No natural
reference-wins/submission-fails region survives scientific validity checks.
There is consequently no eligible ratcheted task for fresh second screening.
No score or model call is fabricated to fill that stage.

All valid numerical concepts score above 0.90 and have no substantive remaining
core failure in the tested regions. The low-scoring experiment fails the
complete-public-objective/valid-reference requirement. **None meets all
acceptance conditions.** No production `participant` is promoted. The four
pilots and complete evidence remain available for inspection.

## 6. Evidence and reproduction

- `decision.json`: exact scores, rankings, audit paths, counts and final status.
- `private/CANDIDATES.md`, `private/RESEARCH_AUDIT.md` and
  `private/sources_manifest.json`: all directions and provenance limitations.
- `private/tournament_summary.json`, `private/runs/pilot` and
  `private/scores/pilot`: actual logs, frozen submissions and case-level scores.
- Each concept's `private/reference`: generators, stored references, baseline
  measurements and numerical checks; audit folders retain fresh inputs,
  protocols, results and preservation hashes.
- `private/final_integrity.json`: final schema, hash, count and decision checks.

From this output root, run `/usr/bin/python private/summarize_tournament.py`
to check original run hashes and aggregate stored scores, then
`/usr/bin/python private/finalize_decision.py` to regenerate the decision and
integrity record. Concept audit reports give their reproduction commands.
These checks do not launch new models.
