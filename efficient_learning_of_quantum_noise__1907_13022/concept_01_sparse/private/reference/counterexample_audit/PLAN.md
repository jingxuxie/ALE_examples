# Bounded counterexample audit

This is an audit of the existing frozen solver, not a pilot, ratchet, replacement pool, or new task. All writes, temporary child directories, cases, predictions, and reports remain inside this directory. Participant files, active pools, evaluator, reference, targets, and frozen submission are protected by before/after SHA256 inventories.

Frozen submission: task-root `private/runs/pilot/submissions/concept_01_sparse.py`, SHA256 `1996fc1f78936055adf84e5ebca607c0dfae8b0b832077e4769f8716891c73a4`.

## Fixed matrix, before any run

Two independently seeded cases per row, twelve total. No retrying, rejection sampling, adaptive seed replacement, or additional cases after inspecting results.

| Region | Qubits | Heavy terms | Groups | Hash bits | Dynamic range | Bin noise / minimum heavy probability | Background |
|---|---:|---:|---:|---:|---:|---:|---|
| Higher load | 40 | 384 | 4 | 7 | 12 | 0.15 | None |
| Sign-noise boundary | 80 | 260 | 4 | 7 | 32 | 0.32 | None |
| Range and dimension boundary | 100 | 480 | 3 | 8 | 9000 | 0.19 | None |
| Nearly equal collision amplitudes | 64 | 352 | 4 | 7 | 1.3 | 0.15 | None |
| Approximately sparse boundary | 96 | 280 | 4 | 7 | 48 | 0.19 | 8192 physical errors, 6% of nonidentity mass |
| Known heteroscedastic errors | 72 | 120 | 4 | 6 | 1000 | 0.13 before row scaling | Per-offset factors 0.45–2.8, independently permuted by group |

Seeds are `810031 + 997*region_index + 17*replicate`, with zero-based indices. Dimensions, Clifford-generated commuting hashes, zero/coordinate/random offsets, independent Gaussian fitted-eigenvalue errors, random arbitrary-weight physical Pauli supports, and positive normalized probability spectra all obey the current contract. No special Pauli labels or singular hash matrices are engineered against the frozen solver. Existing generator routines supply hashes and observations; independent physical Pauli-commutation evaluation checks 32 sampled observations per group and supplies 384 held-out probes. Hash rank and commutation are checked explicitly.

## Reference-success gate and scoring

Run the **unchanged input-only reference** and existing weak baseline under the existing Landlock runner, redirecting only the runner's temporary root to this audit directory. Eligible cases require successful physical output validation, reference score strictly greater than 0.9, reference significant-support F1 at least 0.98, and **uncapped raw reference loss below 0.1**. All exclusions and reasons remain in the report. A failure where the reference also fails is not counterexample evidence and is not replaced by another seed.

Use unchanged `metrics.measure` and `metrics.grade`; each new case has one reference/weak calibration shared by both the reference and frozen submission. There is no tighter grading, changed submission schema, or extra predicted quantity. Diagnostics additionally compare actual recovered labels and probabilities against physical truth and against the reference, including mass of absent heavy labels and errors for atoms above twice the existing floor. These diagnostics distinguish substantive support/probability failures from tiny threshold-crossing disagreements; they are not new score components.

## Static inspection

The frozen solver reads only the input NPZ (`main`, lines 872–877). It contains no planted labels, family/seed switches, cached answer paths, or fixed-width 128-bin assumption. It implements normalized Walsh bins; dimension-aware binary span coordinates; reliability-ordered parity-syndrome decoding (`SoftDecoder`); cross-group validation (`consider`); direct/soft support recovery; pair, XOR-doubleton, and triple recovery; restarts; and constrained weighted probability fitting with an unresolved uniform component. Inverse-noise weighting and residual-adaptive weights are explicitly implemented. This is a general solver for the intended structured sparse inverse problem, not an identity-only or low-weight/dense shortcut. Potential boundary weaknesses must therefore be demonstrated experimentally, not inferred merely from large dimensions or collisions.

## Commands

From the concept directory:

```bash
python -B private/reference/counterexample_audit/audit.py prepare
python -B private/reference/counterexample_audit/audit.py run
```

`prepare` refuses to replace an existing audit plan. `run` never changes inputs and records per-case results before proceeding. It does not launch models or agents. A complete audit without a substantive reproducible failure rejects the proposed counterexample/ratchet and treats this pilot as robustly solved within the tested region; this is not a theorem covering every possible contract-valid input.
