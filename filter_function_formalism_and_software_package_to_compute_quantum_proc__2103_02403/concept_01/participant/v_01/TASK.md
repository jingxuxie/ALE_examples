# Release audit: quantum gate-sequence noise predictor

You own the release decision for a research team's process-prediction service.
Its filter-based calculations are fast and its simple dephasing checks pass,
but the transfer predictions disagree with independent ensemble diagnostics.
Some disagreements change with gate partitioning; others survive refinement
and appear in channel components that average fidelity barely probes.

Diagnose and repair or replace the necessary components. Deliver a reliable,
resource-bounded predictor and evidence explaining which conclusions the
team may draw from it. Do not assume that either the implementation, its
documentation, or the team's current approximation is correct for every
supplied physical regime. The goal is a trustworthy scientific workflow,
not agreement with a particular implementation.

## Supplied workspace

- `workspace/vendor/`: a real multi-file filter-function package, including
  numerical integration, control concatenation, operator bases and quantum
  process conversion. This is a legacy snapshot, not a solved task.
- `workspace/pipeline/`: the team's integration layer and executable baseline.
- `input/real_controls/`: extracted optimized spin-qubit controls; their
  experimental provenance is retained privately for this blinded audit.
- `input/cases/`: controls, physical noise models, and gate partitions for
  development experiments. `input/FORMAT.md` is the complete convention and
  executable contract. There are no hidden device parameters to estimate.
- `input/lab_checks.csv`: a small, noisy set of independent ensemble checks;
  uncertainties are sampling standard errors, not an accuracy guarantee.
- `workspace/diagnose.py`: a deliberately expensive trajectory diagnostic
  supporting the supplied non-white small-system calibration experiments.
  Use it to design discriminating experiments, not as a target-value oracle.
- `workspace/tests/`: small exact representation/invariance checks, not a
  complete validator. Python, NumPy and SciPy are installed; auxiliary
  dependencies are vendored in `workspace/deps` and enabled by `run.sh`.

The development set includes driven Gaussian noise, switching noise, white
noise and colored charge-noise devices. Hidden experiments change physical
noise law, noncommuting controls, correlation structure, segmentation,
leakage geometry and computational scale within the documented contract.
Real-control records retain all segments of the optimized pulse. The
program must infer its behavior from arrays and physics, not case identifiers.

## Work expected

Reproduce the failure. Design tests that separate representation or numerical
errors from a failure of the physical approximation. Repair the pipeline,
choose adequate methods, run convergence and noise-memory ablations, and
rerun the comparison. Account for both full-channel prediction and quadratic
response, including coherent effects and leakage. Demonstrate that any fast
approximation you keep is justified in the regime where you use it.

Do not infer validity just from trace preservation, complete positivity,
Gaussianity of scalar noise, or agreement of one scalar fidelity. Conversely,
do not discard a fast approximation solely because it fails outside its
useful regime. Your release should make defensible accuracy/resource choices.

## Deliver in the writable output directory

- `workspace/` containing the executable repaired system, and `run.sh` with
  the interface in FORMAT.md. Copy dependencies you actually need; do not
  depend on a path outside the two permitted directories.
- `results.csv`: one row for every public case in selected and baseline mode.
  Include `row_id,case_id,mode,infidelity,leakage,coherent_size,k2_norm,seconds,
  peak_rss_mb,artifact`; `artifact` is the relative process-output directory.
- `ablation.csv`: selected, refined and no_memory results for at least two
  non-white public cases. Include the same columns. These must be distinct
  experiments; changing labels or tolerances without rerunning is not enough.
- `scaling.csv`: measured resource use and `segments,dimension` from at least
  three public problem sizes. It may refer to rows in results.csv.
- `figures/primary_result.png` and `figures/robustness_or_scaling.png` with
  the CSV source rows identified in `figures/sources.json`. Use figures to
  show the physical comparison and the accuracy/resource tradeoff.
- `claims.json`: a list of evidence-linked quantitative claims. Each entry
  has `claim_id,text,table,rows,metric,operation,value`; operation is `value`,
  `difference` (row0 minus row1), or `ratio` (row0 divided by row1).
  Support at least one memory claim and one refinement/validity claim.
- `report.md`: a concise release recommendation, competing hypotheses,
  controlled tests, changes made, retained limitations, and interpretation
  of the figures. Include a chronological run → diagnose → revise → rerun
  record with actual artifacts, not just a final method description.

Evaluation reruns the system on undisclosed experiments, recomputes channel
and response errors, checks actual resource use, and audits representative
table rows and claims. It rewards accuracy, worst-family robustness and
efficiency continuously. A cosmetic report cannot compensate for a broken
predictor, and extra figures are not intrinsically valuable.

Start with `bash workspace/run.sh input/cases/calibration_static.json OUT`.
You have one hour for this attempt. Work autonomously and keep all outputs
in the designated writable output directory. No network or outside files
are needed or permitted; do not look for the source paper or hidden labels.
