# Concept C — final tournament summary

Completed: 2026-08-28T15:46:42.196020+00:00.

**Solved; hardness not retained. Passing final-v4 solution demonstrated.** The three-ratchet cap is exhausted; there is no further C search or generation.

**Eight of eight fresh attempts passed their own frozen contracts**, with core/worst scores 1/1 throughout. Both final-v4 fresh attempts (v7/v8) pass. Earlier-generation results are not claims that those earlier tensors pass v4. The preserved privileged portfolio is not counted as a ninth fresh attempt.

## Terminal solution

- Tensor: `attempts/v_8/state.npz`; SHA256 `f3cb3264dfd3898d1fbec6437184174c85b5063c83680e45625b5fe1289fcef5`.
- Actual evaluator: `attempts/v_8_audit/evaluation.json`; audit and embedded manifests: `attempts/v_8_audit/audit.json`.
- v8 minimizes the maximum normalized physics error: **0.419485794001**, versus **0.660537536908** for v7.
- No `champions/generation_4` is created. Existing attempts, champions, archives, participant, evaluator, and private portfolio remain unchanged.

| Final-v4 criterion | Limit | v7 measured | v8 measured |
|---|---:|---:|---:|
| `energy_excess` | 5e-05 | 1.25384930822e-05 | 1.71143993182e-05 |
| `order_max_relative_error` | 0.025 | 0.00647946875836 | 0.00408193182314 |
| `density_max_relative_error` | 0.1 | 0.0133539467659 | 0.00432300663056 |
| `y_max_relative_error` | 0.1 | 0.012780522428 | 0.0104769182011 |
| `composite_order_max_relative_error` | 0.01 | 0.00649158100938 | 0.00242861635039 |
| `three_interval_max_relative_error` | 0.1 | 0.0660537536908 | 0.0419485794001 |

## Actual measured history

| Attempt | Frozen contract | Construction seconds | Checker seconds | Core / worst | Pass |
|---|---|---:|---:|---|---|
| v_1 | critical-vacuum-v1 | 863.229 | 1.304 | 1 / 1 | yes |
| v_2 | critical-vacuum-v1 | 756.549 | 2.094 | 1 / 1 | yes |
| v_3 | critical-vacuum-v2 | 612.896 | 1.250 | 1 / 1 | yes |
| v_4 | critical-vacuum-v2 | 927.579 | 1.257 | 1 / 1 | yes |
| v_5 | critical-vacuum-v3 | 691.938 | 1.068 | 1 / 1 | yes |
| v_6 | critical-vacuum-v3 | 668.098 | 0.899 | 1 / 1 | yes |
| v_7 | critical-vacuum-v4 | 591.761 | 4.265 | 1 / 1 | yes |
| v_8 | critical-vacuum-v4 | 758.220 | 4.391 | 1 / 1 | yes |

All eight actual audit/evaluation JSON files and their embedded `participant_sha256` / `submission_files` manifests were read. Every retained state hash matches its submission manifest; every audit reports a completed, non-timeout run, an empty output at launch, and an unchanged read-only participant. Both final public manifests match the current freeze.

Measured sources:
- v_1: `attempts/v_1_audit/evaluation.json` and `attempts/v_1_audit/audit.json`; tensor `attempts/v_1/state.npz`.
- v_2: `attempts/v_2_audit/evaluation.json` and `attempts/v_2_audit/audit.json`; tensor `attempts/v_2/state.npz`.
- v_3: `attempts/v_3_audit/evaluation.json` and `attempts/v_3_audit/audit.json`; tensor `attempts/v_3/state.npz`.
- v_4: `attempts/v_4_audit/evaluation.json` and `attempts/v_4_audit/audit.json`; tensor `attempts/v_4/state.npz`.
- v_5: `attempts/v_5_audit/evaluation.json` and `attempts/v_5_audit/audit.json`; tensor `attempts/v_5/state.npz`.
- v_6: `attempts/v_6_audit/evaluation.json` and `attempts/v_6_audit/audit.json`; tensor `attempts/v_6/state.npz`.
- v_7: `attempts/v_7_audit/evaluation.json` and `attempts/v_7_audit/audit.json`; tensor `attempts/v_7/state.npz`.
- v_8: `attempts/v_8_audit/evaluation.json` and `attempts/v_8_audit/audit.json`; tensor `attempts/v_8/state.npz`.

## Normalized-physics cross-check

Both tensors were rerun through the frozen checker and still pass. A separate dense transfer eigensolution supplies actual L/R boundaries and lambda for explicit full-site contractions at each audited worst sextuple. Literal own-state cumulant subtraction agrees with the checker. A deterministic complex, parity-preserving nonunitary gauge plus uniform scaling raises the raw canonical defect to approximately 1.5e-8, within the unchanged 2e-8 gate; all original criteria still pass and all 252 normalized K3 values remain invariant to numerical precision.

| Attempt | Independent worst K3 relative error | Gauged maximum K3 relative error | Max absolute change over all 252 K3 |
|---|---:|---:|---:|
| v_7 | 0.0660537535128 | 0.0660537539674 | 3.19189e-15 |
| v_8 | 0.0419485751146 | 0.0419485793643 | 4.85723e-16 |

The JSON summary retains exact scalars, own-state lower moments, left/right residuals, gauge parameters, source hashes, per-family errors, and construction/evaluation metadata. This is a correctness check, not a new search or changed target.

## Freeze and preservation

- All 16 regular participant/evaluator files match `adversary/ratchet_3/freeze_manifest.json`; no symlinks, extra public files, or bytecode caches were introduced.
- Public baseline remains `participant/baseline/state.npz` plus `participant/baseline/README.md` only.
- `adversary/portfolio_g3/` is preserved unchanged; its prior passing generation-privileged result is separate from the eight fresh passes.
- Only `status.json`, `adversary/final_tournament_summary.json`, and `adversary/final_tournament_summary.md` are updated.
