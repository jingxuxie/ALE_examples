# Pilot02 counterexample-guided ratchet audit

## Evidence boundary and pre-build decision

Only the completed valid initial submission in `pilots/02_operator_response/attempt/` and the parent's initial test/challenge reports are being analyzed. The interrupted initial attempt is excluded. Initial participant files and initial test/challenge records remain immutable. No models will be launched here, and no ratchet is justified merely by a sub-unit score.

Measured initial results: Te test `0.860325581824`; Te challenge `0.849963980433`; magnetic Fe challenge `0.999999999260`. The independent original-model response is already accurate to approximately `1e-14` or better. Te's repeated residuals are position coefficients (`0.0200903` relative), centers (`0.00280747` relative), and smaller downstream repaired-response errors. This initially suggests one coupled position/center issue, not two independent failures.

Anti-compression gate: before constructing any fresh held-out pool, distinguish a genuine physical failure from an unspecified representation convention. A ratchet must not count several consequences of one center/connection bookkeeping choice as independent bottlenecks. Nor should the tiny Hamiltonian residual, also present in the supplied starter, become a new numerical trivia task.

The valid submission reconstructs full position coefficients, projects the affine position operator, takes the projected origin diagonal as the repaired centers, and subtracts those centers again. The official reference instead projects the center-subtracted `AA` coefficients as a vector and symmetrizes single-WF centers separately. The original public contract did not explicitly distinguish those two workflows. A numerical source comparison and controlled field substitutions are being used to determine whether this accounts for the entire apparent hard region.

Source anchors (unchanged official pin `e046ddc4bfe026ba1f9af2376f04babac5677425`):
- `wannierberri/system/system_R.py:System_R.symmetrize2` calls operator projection and then center symmetrization separately.
- `wannierberri/symmetry/sym_wann_2.py:SymWann._rotate_XX_L_backwards` rotates stored tensor coefficients.
- `wannierberri/symmetry/sawf.py:SymmetrizerSAWF.symmetrize_wannier_property` and `symmetrize_WCC` apply single-WF property projection.
- https://github.com/wannier-berri/wannier-berri/blob/e046ddc4bfe026ba1f9af2376f04babac5677425/wannierberri/system/system_R.py
- https://github.com/wannier-berri/wannier-berri/blob/e046ddc4bfe026ba1f9af2376f04babac5677425/wannierberri/symmetry/sawf.py
- https://github.com/wannier-berri/wannier-berri/blob/e046ddc4bfe026ba1f9af2376f04babac5677425/wannierberri/symmetry/sym_wann_2.py

## Completed causal analysis

The audit reproduces the parent's valid scores exactly. The diagnostic implementation and full numerical evidence are in `private/reference/ratchet_audit/analyze_valid.py` and `analysis.json`. Only the valid `attempt/` implementation was used; the interrupted initial attempt was never inspected.

| Channel | Te test relative error | Te challenge relative error | Interpretation |
| --- | ---: | ---: | --- |
| H | `7.3364e-9` | `7.3364e-9` | Same tiny discrepancy as the supplied starter, not an independent newly exposed solver defect |
| Position coefficients | `0.0200903` | `0.0200903` | One origin-block center/position projection choice |
| Centers | `0.00280747` | `0.00280747` | Coupled to that same choice |
| Raw Berry | `7.68e-15` | `5.05e-15` | Independently solved |
| Raw optical kernel | `5.68e-15` | `3.06e-15` | Independently solved |
| Repaired Berry | `0.00303233` | `0.0126480` | Downstream of the repaired operator choice |
| Repaired optical kernel | `0.00153152` | `0.00276844` | Downstream of the repaired operator choice |

Over `0.99999999999997` of the squared Te position-coefficient residual lies at `R=(0,0,0)`. Its origin diagonal contributes about `51.13%` of that squared residual. The submitted center shift equals the official repaired `AA` origin diagonal to an absolute residual of `7.093e-10` angstrom. The source reference retains a nonzero origin diagonal (maximum real component `0.01231545` angstrom in the test frame), whereas the submission re-extracts centers from the full projected position and removes that diagonal. Counting center, position, and both downstream response errors as independent bottlenecks would therefore be incorrect.

A diagnostic that independently projects stored `AA` coefficients as a polar vector and centers as single-WF properties, using the supplied symmetry data, changes no response code. It matches official centers to approximately `4e-16` relative and official position coefficients to `3.558e-9` relative. Repaired-response errors fall to approximately `1e-8`–`3e-8`. Its unchanged-weight scores are **0.997443220110** on Te test and **0.997443220470** on Te challenge. Fe remains **0.999999999375**. The remaining approximately `0.00256` Te score loss is overwhelmingly the already-present tiny Hamiltonian discrepancy. These are controlled diagnostic scores, not a newly launched model or a new participant submission.

## Physical versus gauge audit

The nonzero Te response difference is **not entirely a harmless common-origin or orbital-embedding gauge change**. This distinction was tested explicitly, rather than inferred from coefficient errors.

`private/reference/ratchet_audit/gauge_check.py` constructs both the submitted repaired operator and the stored reference operator in the official WannierBerri runtime. It independently evaluates each with official `Data_K_R`, `Omega`, and `Formula_OptCond`. The source evaluator confirms the submitted repaired-model differences:

- Test: Berry `0.003032327873`, full complex optical kernel `0.001531522403` relative error.
- Challenge: Berry `0.012648012298`, full complex optical kernel `0.002768444844` relative error.

The control changes centers by the *actual submitted orbital-dependent center shifts* and compensates the origin diagonal of `AA` so that full position coefficients are unchanged. This is more general than a common-origin shift. Its official Berry and optical responses remain invariant, with maximum relative residuals **1.549e-13** and **8.710e-15**, respectively. The inverse recentering of the submitted operator is invariant to approximately `2e-15`. Reference reexecution itself agrees with stored responses to approximately `1.4e-15` or better.

After removing the harmless recentering part, an off-diagonal on-site position difference remains, with Frobenius norm **0.050475510019 angstrom** in either Cartesian frame. It is explained to relative residual **6.803e-8** by the off-diagonal part of the symmetry-transported center matrix:

```text
mean_g U_g diag(S_g c + (t_g - d_g) L) U_g^dagger
    - diag(separately projected centers)
```

Thus there is a small genuine change in the model's gauge-invariant Berry/transition kernels, not merely a gauge-equivalent output being compared in the wrong representation. However, it comes from **one non-equivalent choice of repair definition**, not an additional Berry or optical implementation failure. Official evaluation reproduces the submitted response on the submitted repaired model. Full raw-model Berry and optical responses already match across both physical families.

## Fairness finding and ratchet decision

**Do not build ratchet_1 from this residual. Report a reference-contract ambiguity instead.** This is not a rejection based on predicting that another agent would solve an easy fault.

The original public contract (`participant/workspace/SCHEMA.md`, model and symmetry sections) defines `connection` as a center-subtracted full-position matrix and asks to project operators and transform/average centers consistently. It does **not** specify the source-specific rule to project center-subtracted `AA` and the center parameters separately, retain a nonzero repaired `AA` origin diagonal, and avoid re-extracting centers from the full affine position operator. The valid solver's affine full-position projection is a reasonable reading of the stated ket action and position definition. The source's different repair rule produces a different physical repaired operator; physical non-equivalence alone does not make the solver wrong under an unspecified target rule.

The narrow empirical evidence therefore establishes:

1. A gauge-sensitive part of the original coefficient/center penalty must not count as scientific hardness.
2. The remaining physical difference is completely explained by an unspecified projection rule. It is not a justified failure counterexample for this frozen public mission.
3. Correcting that rule resolves the apparent operator and downstream response failures together. There is no demonstrated second independent bottleneck after excluding the contract ambiguity and the starter's numerical discrepancy.

Publishing the successful response implementation and asking for this one center-transport term would compress the ratchet into a single bookkeeping/protocol change. Keeping a weaker starting tree and rerunning the same already-solved response kernel under different frames would not create a new independently evidenced failure. Fresh coordinate/gauge cases cannot repair this fairness problem by themselves. No random perturbations, new operator concepts, scoring thresholds, or weight changes were introduced to force difficulty.

Accordingly, **zero ratchets were built and no language-model runs were launched**. There is no fresh confirmation pool or ratchet reference-validation claim. Initial test/challenge records, the initial participant, the valid submission, the active evaluator, and all split/confirmation metadata remain unchanged. Relevant immutable artifact hashes were checked before and after both diagnostics and are retained in `analysis.json`. Original confirmation metadata was not archived/replaced because no replacement pool was created.

The parent's ratchet participant-mount requirement is acknowledged. No ratchet tree exists in this disposition, so the evaluator was not changed to select or mount one. If a future separately authorized, fully specified ratchet is created, its confirmation selector and validated `ratchet_1/participant` mount must be introduced together; infrastructure failures must never be counted as task difficulty.

Machine-readable disposition: `private/reference/ratchet_audit/decision.json`. This report preserves, rather than retroactively overwrites or rescales, the initial numerical grades. The pilot's initial Te score should not be used as evidence of a fair two-bottleneck hard region without first resolving the stated contract defect prospectively.
