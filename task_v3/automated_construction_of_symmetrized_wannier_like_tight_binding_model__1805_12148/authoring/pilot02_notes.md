# Pilot02 — full operator symmetry and Berry response

**Current scoring notice:** the user-required pre-grading audit correction at the end of this note supersedes the original zero-anchored calibration. The active scorer is `post_audit_smooth_v1`. Earlier zero-score reports and descriptions are retained only as legacy evidence, not the current grading rule.

## Pre-build decision and scope

2026-08-28 UTC. Assigned scope: `pilots/02_operator_response/**` and this note only. No fresh agents. The parent runs the four-concept tournament. Existing official source clones and the already-installed `authoring/wb_reference_env` are read-only dependencies; do not modify shared vendor or other pilots.

The public starting capability is an atomic-orbital Hamiltonian-only postprocessing workflow, adapted from the earlier symmetry-averaging approach. It does not include the later WannierBerri real-space operator symmetrizer or Berry implementation. The private capability is the actual later WannierBerri implementation, not a new author-written physical solver.

Anti-compression decision: one general Fourier transform cannot solve the compound mission. Independently scored bottlenecks are (1) spinor/nonsymmorphic real-space orbit closure with the correct antiunitary action and vector position operator, and (2) connection-dependent Berry/optical response, including external position-matrix terms. The response track receives a separate physically valid operator model, so a failed symmetrizer does not erase response credit. Sorted bands, scalar-only averaging, dropping off-diagonal position elements, and ignoring spin order are separate natural weak baselines. Generic group averaging is not claimed computationally intractable; diversity comes from the operator and response integration, not artificial scale.

Primary data are the full official trigonal Te H+position model (24 WFs, 195 raw R vectors, 17,305,196 bytes), with the official bcc Fe H+position model reserved as the magnetic physical-family shift if its reference qualifies. Preserve every orbital and input hopping. Coordinate cases are physical Cartesian frame changes, not random synthetic Hamiltonians. Reserve confirmation coordinates before exposing any reference results.

Private source pin: `e046ddc4bfe026ba1f9af2376f04babac5677425` at https://github.com/wannier-berri/wannier-berri . Modules: `system/system_R.py`, `symmetry/sym_wann_2.py`, `evaluate_k.py`, `data_K/`, and `formula/`. Official tutorial/data pin: `efe56e5b312a903bdbf06dcfc7b5fb8bb44c2afb` at https://github.com/wannier-berri/WannierBerri-tutorial . Data paths: `tutorials/5_symmetrization/{Te_data/Te_tb.dat,Fe_data/Fe_tb.dat}`. Tutorial: https://tutorial.wannier-berri.org/tutorials/5_symmetrization/tutorial_symmetrization-solution.html .

## Qualification status

The pinned official source and symmetry dependencies were installed before this scope assignment in an isolated Python 3.12 environment, `authoring/wb_reference_env`. System Python is 3.10. Qualification and reference generation are now complete. Nothing was installed into the shared vendor directory for this build.

## Built artifact and reserved splits

- Root: `pilots/02_operator_response`. The public tree has a concise `TASK.md`, one full-material unlabeled `input/smoke` case, and an earlier-capability NumPy Hamiltonian-only workspace. The public provenance explicitly calls the starting code an adaptation, not an authentic historical file. Neither `sym_wann_2` nor any Berry/optical solver appears in public Python code.
- Trusted implementation: `private/reference/oracle.py`. It reconstructs the native official model, replaces its matrices with the numerical input, executes the official symmetrizer, and calls official `Data_K_R`, `Omega`, and `Formula_OptCond`. It never looks up expected outputs. `private/reference/build.py` generates immutable numerical labels for inexpensive evaluation.
- Te preserves all 24 spinor WFs and 195 input translations; official joint operator symmetrization expands the support to 483 translations. Its reference projections are `s` then `p`, with the tutorial's spin-block-to-interlace conversion.
- Fe preserves all 18 WFs and 27 translations. It uses the tutorial's actual `sp3d2` plus `t2g` hybrid basis and magnetization along the native z direction. It is not a Te relabelling and is not artificially corrupted to create difficulty. Its stored connection is already nearly symmetric; the magnetic response and orbital convention are the physical-family shift.
- Five scored cases, 42 distinct query momenta total: test has one native-frame Te case; challenge has rotated/block-ordered Te and fresh magnetic Fe; confirmation has different reserved frames, orders, and momenta for both materials. Fe is absent from the public fixture and test manifest. Author-only native Fe qualification files are not scored test cases.
- The confirmation definitions and numerical inputs were reserved before any tournament attempt. No fresh solver agents or tournament runs were launched here.

## Independent validation

`private/reference/validation.json` records official reexecution on every numerical case, not comparison of a stored label with itself. All five cases achieve **1.000**, including **1.000 worst-family score** on challenge and confirmation. Official execution takes approximately 1.2–5.7 seconds per case in the reference environment.

`private/reference/independent_checks.py` independently differentiates the spectral projector and the trace of the position connection on Cartesian momentum stencils, without importing the official response implementation. Across all cases, at step `5e-5` inverse angstrom the maximum Berry relative error is **2.483e-7**, and the maximum full complex Kubo-numerator relative error is **2.201e-7**. Halving the step from `1e-4` produces approximately fourfold error reduction in both observables. This checks the actual displayed Cartesian frames, spin orders, sign, imaginary optical part, external position contribution, and physical units.

Additional checks cover independent Fourier band energies, Hamiltonian Hermiticity, anti-Hermitian optical numerator, positivity of its `-i` Gram tensor, Te's odd Berry response under momentum reversal, magnetic Fe's inversion-even response, R-row permutation invariance, missing-field partial credit, and duplicate-R rejection. The scorer also verifies exact/weak/intermediate numerical endpoints.

An important source convention was discovered rather than hidden: official Te's stored position matrices are not exactly R-adjoint-Hermitian (the repaired storage residual is about `0.08148` angstrom). In `data_K/data_K_R.py:Xbar`, the official response path uses `hermitian=True` for `AA` and its derivatives. The public schema now states this distinction: preserve stored coefficients in operator repair, but use their Hermitian Fourier transform for observables. A mistaken storage-Hermiticity assertion was removed; it remains a reported diagnostic. The independent optical calculation agrees only after honoring this documented convention. The private reference source was not patched.

## Scoring and execution

The evaluator is `private/evaluator.py`, with the requested `--submission DIR --split test|challenge|confirmation --output REPORT.json` interface. It reports `core_score`, `worst_family_score`, `family_scores`, per-case errors and runtime, and top-level errors/runtime. Material families have equal weight. Independent numerical channels are H, position connection, centers, energies, raw Berry, raw optical kernel, repaired Berry, and repaired optical kernel. Original-model response remains independently achievable when repair fails.

Each channel has a smooth error quality calibrated by the actual supplied Hamiltonian-only workflow. The weighted quality is normalized between that weak endpoint (zero) and exact physics (one); there is no all-or-nothing tolerance score. Physical omission is measurable: dropping external position terms gives about `0.5501` relative Berry error on the reserved Te case. Fe's smaller external contribution is retained honestly, not magnified through synthetic modifications.

The evaluator calls the parent's bwrap helper with 180 seconds and 8 GiB per case. Its writable scratch mount is a unique subdirectory under `private/reference`, with only that empty subdirectory mounted, never the reference directory itself. A first isolation attempt placed scratch under `/tmp`, which the helper's tmpfs mount obscured; its return-code-125 reports were rejected and the mount location corrected. Final isolated baseline reports are `private/reference/weak_{test,challenge,confirmation}.json`; inspect their `errors` and return codes, not just their zero score.

Final execution audit: **all five bwrap submissions return code 0, all three reports have empty errors, and baseline scores are 0.000 on every split and material family**. The single unlabeled public smoke check passes finiteness, R uniqueness, and Hamiltonian Hermiticity (maximum residual `4.441e-16`). All pilot Python sources parse. Pilot02 is ready for the parent's tournament; there are no remaining build or reference blockers.

Run from the task root, escalated outside the outer agent sandbox while retaining bwrap:

```sh
/usr/bin/python3 pilots/02_operator_response/private/evaluator.py --submission pilots/02_operator_response/attempt --split test --output pilots/02_operator_response/private/reference/weak_test.json
```

Use the same command with `challenge` or `confirmation`. `private/reference/README.md` gives official build and independent-validation commands. Source/data commit pins, SHA-256 values, exact installed versions, and input/reference hashes are in `source_manifest.json` and `manifest.json`. At build time, the installed `sym_wann_2.py`, `formula/covariant.py`, and `calculators/dynamic.py` were required to match the pinned official checkout byte-for-byte.

## User-required pre-grading scoring correction

The post-build audit correctly identified a violation of the requested **continuous, non-saturating** scoring contract: the original evaluator subtracted tolerances, clipped negative baseline-relative scores to zero, and saturated sufficiently accurate outputs at one. It also capped reported numerical errors at `1e12`. The earlier description of that calibration as adequate was incorrect. This correction was explicitly requested before participant output inspection or grading. Initial participant agents were already running; **no live attempt, agent log, or new participant output was inspected or executed for this audit**.

Only the private evaluator, private validation/rescoring code, and this note changed. Cases, reference/weak numerical arrays, all eight weights, and the frozen public mission/workspace remain unchanged. No models or new cases were added, no fresh agents were launched, and the shared sandbox helper was not edited.

The current component rule is exactly

```text
scale = max(stored_weak_relative_error, 100 * tolerance)
quality = 1 / (1 + 9 * relative_error / scale)
score = sum(existing_weight * quality)
```

There is no tolerance subtraction, affine baseline normalization, score clipping, or artificial error cap. Tolerances only set denominator floors. Valid positive errors retain smooth sensitivity both below the old tolerance and far worse than the baseline. Missing/nonfinite components receive zero quality while other components retain their credit; their error is recorded as null with a diagnostic rather than a fabricated finite error. Exact outputs score one. A weak component that is already accurate legitimately receives substantial credit instead of being forcibly normalized to zero. Per-case raw relative errors, weak errors, and component qualities are retained in reports.

`private/reference/rescore_post_audit.py` reads only the existing reference/weak arrays and author-only legacy validation reports. It generates six new reports and `audit_summary.json` under `private/reference/post_audit/`. Original `validation.json` and `weak_{test,challenge,confirmation}.json` are preserved byte-for-byte, with SHA-256 evidence in the audit summary. Do not overwrite those legacy reports with the historical execution command above. The full reference validator's default destination now lies under `post_audit/` as well.

Measured post-audit scores:

| Split | Official reference | Stored weak core | Stored weak worst family |
| --- | ---: | ---: | ---: |
| test | 1.000000 | 0.187443290019 | 0.187443290019 |
| challenge | 1.000000 | 0.300891022795 | 0.187443290021 |
| confirmation | 1.000000 | 0.300891022787 | 0.187443290009 |

The weak mean across all five cases is **0.278201476237**. The pooled material-balanced mean is **0.300891022792**; Te scores about `0.18744329`, and magnetic Fe about `0.41433876`. These are measured credits for the unchanged stored Hamiltonian-only baseline, not a new participant grade. Both definitions of mean are stated because the five-case pool contains three Te and two Fe cases.

All exact stored references score **1.000**, with **1.000 worst-family scores**. Applying the new formula to the retained raw errors from the earlier independent official reexecution gives a minimum score of **0.999999999230**, safely above the required `0.9`. The physics qualification itself was not rerun or changed. Scorer checks verify strict decrease from zero through sub-tolerance errors, across and below the weak endpoint, and beyond the removed `1e12` error cap; missing and nonfinite response fields lose only their component credit. All legacy report hashes and the case-manifest hash remained unchanged.

Reproduce this audit without launching a participant:

```sh
PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 /usr/bin/python3 pilots/02_operator_response/private/reference/rescore_post_audit.py
```

The current grader is ready for the parent's first participant-output inspection and grading under the corrected rule. Shared sandbox mount-order/security changes remain the parent's responsibility.
