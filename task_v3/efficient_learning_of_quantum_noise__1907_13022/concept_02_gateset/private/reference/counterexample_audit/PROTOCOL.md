# Bounded counterexample audit protocol

All writes, including subprocess staging and numerical caches, stay inside this directory. Active participant files, pools, scoring, targets, evaluator, reference implementation and the frozen submission are preserved and hash-checked. Python bytecode writes are disabled. No agents or new models/concepts are launched.

The frozen submission is the parent task's `private/runs/pilot/submissions/concept_02_gateset.py`; its immutable SHA-256 is `05534f2e05f7c85152b909d8a4de8ebbc2023410e93c57f96bd7a1a26f6cc216`. The actual resolved path and hashes of all protected artifacts are in `preservation_before.json`.

## Predeclared cases

Nine fresh cases use the original 20–24-qubit contract, unchanged numeric keys and unchanged local positive Pauli-generator/SPAM model. No labels, family IDs or seeds are added to solver inputs. All interaction and noise-factor graphs remain connected.

1. 20-qubit X-sector-only calibration, seed 9050101.
2. 20-qubit Y-sector-only calibration, seed 9050103.
3. 24-qubit site-dependent X/Y/Z-sector calibration, seed 9050111.
4. 20-qubit stronger anisotropic pair crosstalk and correlated readout, seed 9050201.
5. 24-qubit additional distance-two two-site gate-noise factors, seed 9050203.
6. 20-qubit non-involutory locally compiled Clifford gates and asymmetric correlated SPAM, seed 9050209.
7. 20-qubit high-shot short-circuit anchors and low-shot amplification, seed 9050301.
8. 24-qubit high-shot amplification with lower-shot anchors, seed 9050307.
9. 24-qubit gate-dependent shot imbalance with informative short anchors, seed 9050311.

Rotated sectors conjugate the complete gate library and observation bases by product single-qubit Cliffords. Fresh lab-frame anisotropic physical rates are sampled afterward. This changes which error directions calibration probes; it is not a clerical channel/qubit-ID trick. Compiled gates retain two-site ideal blocks, keeping structural dependency scopes at most four sites. Additional crosstalk remains in the existing two-site ansatz; no latent errors or model misspecification are introduced.

Model-derived independent root rows are added within the appropriate calibration sector. All held-out predictions are exactly calibration-identifiable. Held-out circuits use new compositions of 3–14 library operations with initial observables of weight 1–3, deliberately retaining measurable contrasts rather than manufacturing a low-signal failure. There are 112 query combinations and 128 held-out means per case. Unidentified query coordinates are never scored.

## Mandatory reference qualification

A high calibrated score alone is not accepted as evidence. Every counted case must satisfy all of the following:

- Exact reference structural and calibration identification.
- Reference normalized query loss, raw supported-query squared error, and prediction loss each at least 10 times lower than the weak baseline, including prediction error restricted to held-out absolute means at least 0.1. The final summary independently recomputes the raw supported-query check from saved arrays.
- Absolute reference prediction RMSE below 0.02 and normalized query RMSE below 0.003.
- At least 24 supported queries and 32 held-out absolute means at least 0.1.
- Expected Fisher rank equals calibration rank, prediction standard-error 95th percentile below 0.025, and normalized query standard-error 95th percentile below 0.005.
- Independent bit-Pauli transfer construction exactly reproduces 64 sampled circuit rows/signs and every query row. Feasible positive-rate calibration-null perturbations leave all scored targets invariant.
- The unchanged reference actually runs on input alone under the existing 120-second/3-GiB Landlock evaluator. The frozen solver uses the same execution path and exactly the same per-case calibrated scales.

Fisher and planted-rate calculations are auditor-only qualification diagnostics, never reference inputs. Qualification is reported even when it fails; unqualified cases cannot establish either a counterexample or robust success. The original grading formula and component weights are imported unchanged. No active task ratchet is applied.

## Method inspection

The frozen solver is not merely given a matrix and pseudoinverting it. It implements signed bit-packed Clifford propagation, sparse local-generator embedding, a reduced SPAM/gate gauge pullback, finite-design row-space checks, equivalent-parameter/experiment compression, and positive-rate binomial likelihood fitting. It uses a bias-corrected log fit only as an initializer. Its broad method therefore plausibly covers the tested source-model shifts; this audit looks for genuine physical/statistical limitations rather than a hidden-ID trick.

No extended-scale cases are planned in this bounded run. A 40–64-qubit representation/runtime limitation, if investigated later, must be explicitly separated from the original-domain verdict.

## Reproduction

From this directory, with the original frozen submission and parent artifacts still present:

```bash
PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 python -B run_audit.py --resume
```

`--case NAME` permits a bounded single-case replay. Results, input-only outputs, hidden audit targets, timings, memory and diagnostic checks are saved only below this directory.
