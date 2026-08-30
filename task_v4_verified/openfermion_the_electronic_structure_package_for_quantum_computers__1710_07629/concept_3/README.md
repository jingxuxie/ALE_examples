# concept_3 — builder handoff (private)

The participant tree and evaluator source are frozen and ready for an independent
participant launch. Only `participant/` belongs in the participant release.
The main-supplied `participant/workspace/audit_isolation.py` and
`evaluator/hidden/isolation_canary.txt` are preserved.

## Contract

- Participant entrypoint: `python3 solver.py REQUEST_JSON PREDICTIONS_JSON`.
- Grader: `python3 evaluator/evaluate.py SUBMISSION_DIR [--report REPORT_JSON]`.
- Public guarded development: append `--split validation` to the grader command.
- Resource contract: 25 wall/CPU seconds, one CPU, 2 GiB address space; training
  one hour/four threads/8 GiB. The fitted inference baseline imports NumPy only.
- The same public law produces 1,536 training, 256 validation and 256 hidden
  instances, balanced across four families with an independent 8/10-site mixture.
- Spin labels are fixed-Sz differences, not certified singlet–triplet gaps. No
  physical sign or floating-point negative difference is clipped.

## Fixed target rationale

Before hidden generation, `participant/input/scoring.json` fixed global RMSE
limits of 0.030 charge and 0.020 spin, and family limits of 0.050 and 0.035.
These measure errors in the base hopping unit, far above the label uncertainty
but small compared with typical finite-cluster responses. Paired observables and
all-family gates prevent the easier charge or geometry trends from masking spin
and frustration errors. The 8/10-site mixture avoids relying on an artificially
tiny deadline for 4,900-dimensional eight-site sectors alone.

This remains a `hard_open_candidate`: no budget-valid passing predictor is known
to the builder, and no impossibility or achievability claim is made. A genuinely
fast direct or hybrid solver remains legal; solver amortization is not prescribed.

## Evidence

- `attempts/baseline_validation.json` and `attempts/baseline_hidden.json` are the
  final fitted baseline's guarded reports. The weights fit training labels and
  select hyperparameters only on public validation. Training completes in seconds.
- `attempts/direct_ed_timing.json`: conventional matrix-free ARPACK, tolerance
  1e-5, takes 108.2 CPU seconds for the full public batch and achieves numerical
  reference accuracy. CSR and tensor implementations were compared first.
- `attempts/direct_fast_timing.json`: a looser 0.01-tolerance, 12-vector control
  takes 57.7 CPU seconds and also misses accuracy (charge 0.03169, spin 0.04018).
  `attempts/direct_fast_budget.json` runs that same control at the actual 25-second
  limit. These are measurements, not a lower bound on all possible solvers.
- Shared-host contention substantially inflates wall times. CPU times and both
  wall and CPU limits are reported; the full controls exceed even the CPU cap.
  `evaluator/hidden/pilot_contended_report.json` retains the original CPU-0 pilot;
  `pilot_report.json` is a later optimized, single-CPU rerun, not a target reset.
- `evaluator/hidden/source_validation.json` records independent full-Fock/analytic
  limits, RDM energy/trace/occupation and derivative checks. `data_audit.json`
  checks disjoint splits, replay of the common law, signed labels and 24 tighter,
  independently started, site-permuted recomputations across every split/family/size.
- `adversary/test_report.json` and `test_log.txt` retain all 22 passing safety and
  malformed-output tests. `dependency_report.json` records imports inside the actual
  child. sklearn imports with denied-proc/joblib serial warnings; baseline inference
  does not import it. `interface_report.json` verifies scalar permutation invariance.

One baseline-only bug was found by the public permutation check: scaling an
exactly-zero physical feature by floating-point noise amplified roundoff. A
1e-8 scaler floor fixes it. The original reports remain as
`attempts/baseline_initial_*.json` and `adversary/interface_initial_report.json`.
This correction was driven by the public invariance failure, not hidden-score
optimization. No distributions, labels, tolerances, budgets or target thresholds
changed. The final symmetry error is below 2e-13.

The evaluator never imports submitted code. Its exec-only Landlock/seccomp helper
is copied/adapted locally from the provided QAOAKit isolation infrastructure; there
is no runtime dependency on that other task. It fails closed if Linux isolation
cannot be installed. `evaluator/hidden/SOURCE.md` records paper/source grounding
and numerical limitations. All per-sector residuals and energies are retained.
