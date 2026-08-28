# Author handoff: c02_dmft

Only `participant/` is the public task package. It is frozen after initial construction. `attempt/` was created empty; no pilot agent was run by this author helper, and no author solution was placed there. Main owns subsequent participant attempts. Do not rerun `reference/build.py` after the public freeze: it also regenerates the public excerpts and two samples.

## Evaluation

From the pilot root:

```
python private/evaluator.py --submission attempt/solve.py --split core --report core_report.json
python private/evaluator.py --submission attempt/solve.py --split challenge --report challenge_report.json
```

Set `ALPS_EVAL_WRAPPER` to the orchestrator's shared wrapper to enforce the external network-disabled filesystem sandbox. The evaluator wraps its normal command using `--participant`, `--submission`, `--work`, `--timeout`, and `--` exactly as requested. It collects `_resource.json` seconds and maximum RSS before temporary cleanup. The wrapper invocation may require escalation for bubblewrap. Without the wrapper, the evaluator isolates files, arguments, environment, and working directory but does **not** claim an OS security boundary.

Each submission process sees a fresh copied `solve.py`, an unlabeled `input.json`, and an output destination. No reference filenames, private case paths, answer data, anchor scales, parent environment, or private Python modules are passed to it. Only the submitted entry file is copied; the contract requires a standalone file. The shared wrapper additionally exposes the public participant package and the submission parent by design.

The report has `mean_core_score`, `worst_family_score`, `families`, and per-case component scores, errors, and times. For compatibility, `mean_core_score` means the mean of the **requested** split even when `split="challenge"`. Each split is family balanced. The finite-output/shape/schema checks fail the entire case closed. Each case gets 120 seconds, one numerical-library thread, and the wrapper's default memory limit. The evaluator kills timed-out process groups.

## Scientific coverage and provenance

The core has six cases, two each of Fourier integration, multiband AFM self-consistency, and signed Legendre estimation. The challenge has nine cases, three per family. Hidden inputs and answers are disjoint from the two tiny public samples. `reference/manifest.json` names all inputs, precomputed answers, and frozen component scales; `challenge_pool/` contains challenge inputs only.

The public executable is a **translated adapter**, not raw original ALPS or a demonstrated 2011 checkout. The exact pre-fix functions and their original source notices are extracted from the immediate parents of three official fixes. `reference/source_manifest.json` pins those revisions, paths, start lines, and SHA-256 values; `reference/upstream/` holds the six unmodified fetched blobs. The full upstream source tree outside this pilot was not edited or used by submitted code.

- AFM: `2fa76e234a64cefa0ccb00a7b82b0d85a2f3023e`, parent `18d8474e9150a5d8a4cdccf32c538471dc9f7b17`, `applications/dmft/qmc/hilberttransformer.C`. The old stride-2 half-bound loop with doubled indexing visits only selected pairs. In particular, six flavors visit pairs (0,1) and (4,5), not (2,3); the adapter preserves that exact pattern, not a fabricated first-band-only rule. New Weiss values, the derived lattice function, hybridization, and time transform are all scored. The supplied discrete DOS measure replaces file parsing and integration setup, not the pair physics.
- Signed Legendre: `272d6e3531c2b0d2a60f3e53b0898b74b72aa698`, parent `73b3310067a2a332bab1a4da871874f3cf71d3a8`, `applications/dmft/qmc/hybridization/hybmatrix.cpp`. The old raw measurement applies the configuration sign to both `M_ji` and the bubble sign. The adapter retains that arithmetic and performs the usual downstream square-root normalization and sign-mean division explicitly. These are deterministic nonsymmetric event-matrix fixtures, not claims about the prevalence of signful production segment runs. Signed coefficients, finite-polynomial Matsubara reconstruction, and the improved-estimator ratio are independently scored.
- Fourier: `e2e9e16e18f3e54855e438274d463f5c046d9651`, parent `73b3310067a2a332bab1a4da871874f3cf71d3a8`, `applications/dmft/qmc/fouriertransform.C`. **This historical guard is latent, not production-reachable through the concrete SITES=1 transformers.** Its post-fix all-zero-tail shortcut is not a valid general physical theorem and is not the oracle. Every task channel is active. Tridiagonal real Hamiltonians supply genuine off-diagonal resolvents with either only the third moment nonzero or all first three moments zero. The latter must remain nonzero. The matrix-entry adapter extension and its mathematical convention are explicit in the public contract. A blind application of the historical guard correction does not solve this task.

The available external-solver output and solver-factory commits are deliberately not scored: clerical dispatch would not add an independent scientific bottleneck. No claim is made that these 2026 pre-fix snapshots are byte-identical to the release discussed by the target paper.

## Independent references and calibration

`reference/strong.py` is a standalone author-only strong adapter. Its AFM and Legendre reductions follow the corrected source arithmetic; its Fourier transform implements the explicitly extended contract without either historical zero-tail guard. It does not import the weak adapter.

`reference/oracle.py` generates the stored answers independently: paired positive/negative Matsubara sums; weighted inverses of explicit two-by-two AFM lattice resolvent matrices; SciPy Legendre polynomial evaluation and spherical-Bessel transforms rather than the strong adapter's recurrence and Gauss-Legendre frequency integration. Fourier round-trip answers are the input coefficients, checked against the separately computed transform. `reference/reference_checks.json` records all component discrepancies and weak errors. No reference code is executed during scoring.

For each component, the stored scale is `max(weak_error/4,1e-8,100*strong_crosscheck_error)` and the score is `1/(1+normalized_rms_error/scale)`. Thus a genuinely faulty weak component anchors at 0.2, whereas an already-correct component is near one. There is no correctness threshold or score plateau. The family mean exposes independent failures instead of rewarding only a pipeline's final ratio.

`reference/validate.py` checks single-band and sign-free legacy controls, AFM duplicate-band and band-permutation invariance, signed weight rescaling and configuration splitting, physical zero-moment nonzero channels, endpoint jumps, and independent integration of the tail polynomials. It also runs both adapters through the actual evaluator on both splits and checks missing/malformed/wrong-shape/nonfinite/boolean outputs, nonzero exits, absent submissions, and timeouts. Reports and summaries remain private. The source algorithms are translated and independently checked; the full upstream C++ application was not compiled or run.
