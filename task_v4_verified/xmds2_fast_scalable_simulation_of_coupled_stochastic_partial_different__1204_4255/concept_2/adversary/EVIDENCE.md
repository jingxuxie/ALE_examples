# Privileged validation evidence

This is authoring evidence, not a tested fresh-agent result. Empirical status remains `pending_tournament`; no agents were launched here.

## Runtime and feasibility

- Weak baseline: three fixed-seed screening trials in 1.50 seconds. Full evaluator: valid, not passed, core/worst-family score 0.04910886774399552; 22.46 wall seconds and 56.93 MiB peak RSS.
- Initial locally optimized candidate: valid, score 0.8262444448531662. Every family exceeded the density-gap target, but `shape_minus` failed the 1e-4 temporal certificate with 1.2102955804776544e-4. This is a tested negative control for accepting the gap alone.
- After freeze, a fixed four-point duration check selected one candidate. `robust_candidate.evaluation.json` certifies **valid=true, passed=true, core_score=worst_family_score=1**. Minimum conservative density gap is **0.3047395523690949**, maximum temporal certificate **8.949305456839472e-5**. All five families pass all guards and all numerical-reference checks. Evaluation used 33.08 wall seconds, 31.32 CPU seconds, 57.39 MiB RSS under competing local load.
- The four screening durations had worst-family scores approximately 0.9640, 1, 0.9759, 0.9402. Only the selected candidate was fully certified. Do not interpret screening counts as a fresh-agent hit rate.
- Earlier 24-case random/nominal calibration and 160-proposal local search are retained for provenance. They used cheaper references and some early probes used fewer output times. They are not 24 or 160 final-protocol validation trials. No statistical tournament hit-rate claim is made.

## Numerical and validity controls

`test_controls.py` rejects malformed/empty/deep JSON, duplicate keys, NaN/infinity, booleans, out-of-range values, nested values, extra parameters, forged scores, oversized files, missing files, directories, invalid UTF-8, symlinks, and FIFOs. Invalid data produces finite zero-score objective JSON without running submitted code. Fixture cleanup stays inside `adversary/`.

Numerical checks verify exact linear propagation, strict initial support |k|≤3, padded cubic convolution against direct convolution, and fourth-order convergence against DOP853. Public and frozen private kernels/protocol are checked byte-for-byte. Per-family reference evaluations report distinct temporal, spatial, and independent-method deltas; the uncertainty safety factor and acceptance caps are public.

## Freeze and isolation

`evaluator/hidden/freeze_manifest.json` fingerprints every public task/kernel/protocol file and the evaluator implementation. No target or participant asset was changed after the successful four-point feasibility check. The evaluator reads data only and runs frozen code with `/usr/bin/python3 -I -B`, a fixed working directory, controlled thread environment, wall timeout, CPU limit, and address-space limit. Participant code and private witness artifacts are never loaded from the submission directory.

Baseline and proof JSON files are ready to rerun. Keep this directory and all evaluator artifacts outside the tested agent's readable sandbox. Only `participant/` is the participant bundle.
