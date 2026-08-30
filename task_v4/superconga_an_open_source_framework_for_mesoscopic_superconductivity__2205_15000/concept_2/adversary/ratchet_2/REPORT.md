# Generation-3 champion ratchet

Selected case: `islands16_v6_eta0.01`. Acceptance thresholds stay **.96 core / .94 worst**.

## Algorithm provenance and strength

Fresh generation_2 construction/research source, not static design: optimize.py, continuation.py, discrete.py research snapshots; identical to preserved source. The generation_2 final submission retained design.json, construction sources, and research outputs; generation_1 alone cleaned down to design.json.

Original 48 seeds 0..47, linear/log/sqrt modes, SLSQP exact count equality, all six binary penalty weights .02/.1/.3/1/3/10, maxiter250/stage and ftol1e-9

This is NOT an old-layout/new-fingerprint comparison. Blind optimization calls the preserved construction algorithm. The gen2 control reproduces its exact seed-7 solution. Eight original 450-iteration L-BFGS starts, their 300-evaluation least-squares continuations, and eight 350-evaluation cold least-squares starts are additionally attempted on the primary; completed and pending runs are distinguished in the source records.

## Physical controls

Four geometries (14,16,18,20) cross V=3.2/6 and eta=.01/.02. Two matched 12x12 island controls supplement the original gen2 target. Candidate counts are 96/144/192/256 and normal budgets 36/54/72/96: exactly 3/8 normal material, open boundaries, fixed prescribed chiral-gap model. Four interior corners are held superconducting on sizes 14/18 solely to retain the exact fraction. Masks are first-feasible correlated metallic islands, selected before optimization, never by failure or spectral fingerprint. Each geometry uses the same mask across V and eta.

All spectra are uniformly sampled on [-.3,.3] at step eta/2 (four samples per Lorentzian FWHM). The 16x16 case was predeclared as the moderate-size full-strength primary before fitting; 18/20 are scaling controls, not the selected obstacle.

## Measured sweep

Screening = seeds 0,1,2, six stages, maxiter80; it is NOT equivalent to the original-strength test. Full = all six stages with original maxiter250. Scores below include all scored stages, including partial runs. Raw RMSE prevents clipped zero scores from hiding differences. Runtime sums are aggregate process time, not elapsed sidecar time.

| Case | Completed runs | Full seeds | Stages | Best core | Best worst | RMSE | Best valid core | CPU seconds |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| generation_2_control | 4 | 4 | 24 | 1.000000 | 1.000000 | 0.000000 | 1.000000 | 444.07 |
| islands12_v6_eta0.01 | 51 | 48 | 306 | 0.201087 | 0.142485 | 0.798913 | 0.160182 | 7943.52 |
| islands12_v6_eta0.02 | 3 | 0 | 18 | 0.301723 | 0.293168 | 0.698277 | 0.301723 | 222.38 |
| islands14_v3.2_eta0.01 | 3 | 0 | 18 | 0.274103 | 0.268045 | 0.725897 | 0.274103 | 406.18 |
| islands14_v3.2_eta0.02 | 3 | 0 | 18 | 0.478903 | 0.443830 | 0.521097 | 0.458586 | 395.33 |
| islands14_v6_eta0.01 | 3 | 0 | 18 | 0.203829 | 0.196705 | 0.796171 | 0.116951 | 692.35 |
| islands14_v6_eta0.02 | 3 | 0 | 18 | 0.420005 | 0.400264 | 0.579995 | 0.312941 | 521.10 |
| islands16_v3.2_eta0.01 | 3 | 0 | 18 | 0.206629 | 0.185088 | 0.793371 | 0.083816 | 1150.08 |
| islands16_v3.2_eta0.02 | 3 | 0 | 18 | 0.491425 | 0.466913 | 0.508575 | 0.454579 | 937.57 |
| islands16_v6_eta0.01 | 67 | 48 | 330 | 0.314648 | 0.291193 | 0.685352 | 0.294183 | 61839.77 |
| islands16_v6_eta0.02 | 3 | 0 | 18 | 0.437206 | 0.397084 | 0.562794 | 0.393625 | 1289.89 |
| islands18_v3.2_eta0.01 | 3 | 0 | 18 | 0.299874 | 0.280485 | 0.700126 | 0.265392 | 2129.40 |
| islands18_v3.2_eta0.02 | 3 | 0 | 18 | 0.562724 | 0.552720 | 0.437276 | 0.446593 | 1856.53 |
| islands18_v6_eta0.01 | 3 | 0 | 18 | 0.266436 | 0.235371 | 0.733564 | 0.234745 | 2858.01 |
| islands18_v6_eta0.02 | 3 | 0 | 18 | 0.518120 | 0.516259 | 0.481880 | 0.456827 | 2158.92 |
| islands20_v3.2_eta0.01 | 1 | 0 | 16 | 0.344878 | 0.326259 | 0.655122 | 0.344878 | 3337.97 |
| islands20_v3.2_eta0.02 | 3 | 0 | 18 | 0.560056 | 0.537000 | 0.439944 | 0.560056 | 3378.97 |
| islands20_v6_eta0.01 | 0 | 0 | 12 | 0.231837 | 0.204487 | 0.768163 | 0.067946 | 3313.91 |
| islands20_v6_eta0.02 | 1 | 0 | 16 | 0.423873 | 0.416305 | 0.576127 | none | 3516.00 |

## Candidate evidence

Original-strength continuation: 48 complete seeds, 288 stages, no pass. All-method total: 330 scored stages, 73813 function evaluations, 61839.77 CPU-seconds. Best valid core/worst = 0.29418313/0.28124315; best score even ignoring fabrication validity = 0.31464753. Thus failure is not just count/connectivity rejection.

Known witness official core/worst = 0.99999999999985/0.99999999999980; checker wall time 0.847s. Matrix/LDOS/direct-resolvent validation, all three objective gradients, least-squares Jacobians, and low-rank swap-helper consistency are independently checked.

Jacobian condition numbers: witness 16019.5, uniform 481445.8, best valid relaxed endpoint 4083.6. Binary-layout entropy before connectivity: 133.57 bits versus 57.80 bits at 64/24. This is a search-space description, not a hardness proof.

Refined-grid rescoring of the best valid blind mask:
- 121 energies: core=0.29418313, worst=0.28124315, RMSE=0.70581687.
- 241 energies: core=0.29534678, worst=0.28095455, RMSE=0.70465322.
- 481 energies: core=0.29589286, worst=0.28078939, RMSE=0.70410714.

## Handoff

- Public device: `adversary/ratchet_2/cases/islands16_v6_eta0.01/public/input/device.json`
- Public target: `adversary/ratchet_2/cases/islands16_v6_eta0.01/public/input/target.npz`
- Private feasible witness: `adversary/ratchet_2/cases/islands16_v6_eta0.01/private/design.json`
- Frozen hashes, thresholds, and algorithm provenance: `proposal/freeze.json`.

The failures identify finite-budget many-inclusion nonlinear inverse-design/search obstructions for this champion, not impossibility or one-hour hardness. A new method, more starts, or longer runs may still succeed. No live assets or champion sources were changed; no agents were launched.

## Final completion audit

All 48 six-stage continuation seeds AND all 24 auxiliary fits are now complete: 312 original-strength optimizer stages, 71948 function evaluations, 60341.10 CPU-seconds, zero passes. This excludes the extra three lower-budget primary screens.

The matched 12x12 island target also survives 48 complete original-strength continuation seeds; best valid core=0.160182. Therefore many-island geometry itself is an obstruction for this finite portfolio; dimension growth is not isolated as the sole cause. The selected 16x16 case combines that geometry with the larger 144/54 binary design space.

All primary original-strength continuation AND auxiliary branches are complete. Any listed pending runs belong to lower-budget geometry screening and are not counted as complete failures.
- Pending broad-screen jobs at final audit: islands20_v6_eta0.01: continuation_0_80, continuation_1_80.
- Pending broad-screen jobs at final audit: islands20_v6_eta0.02: continuation_0_80.

## Housekeeping closure

Private screens: 53 completed, including 11 of the 12 20x20 screens. The remaining `islands20_v6_eta0.01 / continuation_0_80` screen was interrupted after five recorded stages and is canceled/incomplete, NOT a failed completed run. No private screening processes remain. Earlier pending-job lists are historical freeze snapshots; `housekeeping.json` is the final job-status record.

Provenance is corrected: generation 2 retained design.json, sources, and outputs; only generation 1 cleaned down to design.json. The parent-corrected proposal was left unchanged. Historical execution logs are retained verbatim. No live participant/evaluator/generation-3 target files were touched, and no additional search was run.
