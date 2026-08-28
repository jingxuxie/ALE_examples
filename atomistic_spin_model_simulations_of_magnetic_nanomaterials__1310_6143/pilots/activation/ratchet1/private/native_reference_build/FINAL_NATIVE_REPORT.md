# Native reference handoff: READY and frozen

Six initial and five challenge cases are certified. The six initial case/solution/validation files and manifest are unchanged; only two newly seeded challenge cases were appended. No public, grader or upstream implementation is modified.

## Source and runtime

Spirit revision: `e82250d3b14411c2c2fa292d143f13e3e111ad8c`.
Native library SHA256: `88d4356e5817318fee0d8a96001163f7ba0491ba2bcb506803f264f4e8fb419b`.

The original nine builds use `build.py`; the two largest use `large_extension.py`. The latter reuses one native state, certifies both mechanisms, then calculates full-size native sparse HTST only for the lower saddle. Both mechanisms also receive matching N128 native dense/sparse checks. This removes duplicate work, not a scientific check on the selected reference. Total warm time includes small calibration, preparation, both GNEB saddles, independent spectra/FD, four downhill descents and selected native HTST. All runs impose2GiB; the two largest also have external90s timeouts.

- N3072: 30.311811939s total; sparse HTST 19.807415153s; peak RSS 147500KiB.
- N4096: 54.652617689s total; sparse HTST 36.557756453s; peak RSS 212268KiB.

## Exact maximum errors

Values are binary64 results printed to17 significant digits. The machine-readable report identifies every maximizer. 'All certificates' also includes small calibrations and competing mechanisms; missing full-size HTST for a higher large-case competitor is not treated as a zero error.

| Metric | Selected11 references | All native certificates |
|---|---:|---:|
| saddle_residual_meV | 9.5540632688644129e-12 | 1.8236702643557334e-11 |
| minimum_A_residual_meV | 5.0518765909367021e-10 | 5.0518765909367021e-10 |
| native_sparse_log_omega_error | 3.8766775123377784e-08 | 4.2888474993674208e-08 |
| hessian_fd_max_error_meV | 4.2069059347227267e-10 | 4.2069059347227267e-10 |
| native_barrier_absolute_difference_meV | 0.00037961388005935959 | 0.00037961388005935959 |
| native_barrier_error_fraction_of_rounding_bound | 0.28747512480357085 | 0.28747512480357085 |
| native_downhill_endpoint_max_distance | 3.8560735623962571e-09 | 5.5861953181854232e-09 |
| native_downhill_residual_meV | 2.1301352237614612e-08 | 2.1301352237614612e-08 |
| native_dense_minimum_spectrum_max_error_meV | 1.7656144137845331e-06 | 1.7656144137845331e-06 |
| native_dense_saddle_spectrum_max_error_meV | 1.8737192988282914e-06 | 1.8737192988282914e-06 |

The native Python getters use `ctypes.c_float` for energies, HTST scalars and returned eigenvalues even with the double engine. Full dense-spectrum discrepancies are therefore reported at getter precision. Native barrier differences are bounded using float32 total-energy rounding; all observed differences remain inside that bound. Full output spectra and cancellation-resistant barrier sums use double precision. Native LLG's stopping metric is not asserted to equal the independently recomputed maximum Cartesian tangent norm; both measured downhill residuals and final endpoint distances are reported above.

## Mechanisms and scientific caveats

- `ratchet1_initial_boundary_localized_86421001`: right-minus-left barrier = 0.018815448789920142meV; both saddles have native GNEB and distinct-basin descents.
- `ratchet1_initial_boundary_localized_86421002`: right-minus-left barrier = 0.017402614543731376meV; both saddles have native GNEB and distinct-basin descents.
- `ratchet1_initial_soft_interface_86421003`: right-minus-left barrier = 0.53705032932451058meV; both saddles have native GNEB and distinct-basin descents.
- `ratchet1_initial_soft_interface_86421004`: right-minus-left barrier = 0.54003061363295424meV; both saddles have native GNEB and distinct-basin descents.
- `ratchet1_challenge_boundary_localized_90312001`: right-minus-left barrier = 0.023304937189240205meV; both saddles have native GNEB and distinct-basin descents.
- `ratchet1_challenge_soft_interface_90312002`: right-minus-left barrier = 0.53791467933062709meV; both saddles have native GNEB and distinct-basin descents.
- `ratchet1_challenge_boundary_localized_90544001`: right-minus-left barrier = 0.023814522295464435meV; both saddles have native GNEB and distinct-basin descents.
- `ratchet1_challenge_soft_interface_90544002`: right-minus-left barrier = 0.54655649157101394meV; both saddles have native GNEB and distinct-basin descents.

All stored saddles have exactly one negative mode and no zero modes. The smallest positive saddle eigenvalue is 0.19308324876460858meV; the smallest unstable magnitude is 0.12841568051453045meV. Minimum barrier/kBT at0.5K is 19.049213855640307.

Coherent controls also have two cold21-image native GNEB paths that recover the same saddle. Long-chain references use trusted localized continuation, independently refined on the full chain. This is a warm author-reference construction, not a cold global-search timing claim. Left/right comparisons include the close boundary barriers, but do not prove global optimality over every possible saddle. Close channels can both matter to a physical escape rate; the contract deliberately reports one selected saddle and its static Omega0, not a sum over channels or a full dynamical/experimental rate. No zero-mode-volume, quantum correction or rotated-native-Hessian capability is claimed.

## Freeze and reproduction

`frozen_reference_hashes.json` covers all33 case/solution/validation files plus both manifests. `native_error_report.json` contains exact maxima and case identifiers. Existing build-time source hashes are retained in split provenance; extension provenance records new seeds90544001/90544002 and independently changed exchange, easy anisotropy, fields and boundary/interface parameters within the existing ranges.

Use pinned `authoring/python_runtime` on PYTHONPATH and single-thread BLAS/OpenMP. Rebuild commands are `python -B private/native_reference_build/build.py --split initial`, `--split challenge`, then `python -B private/native_reference_build/large_extension.py boundary_localized` and `soft_interface`, then the append/report script. Do not rerun builders against frozen directories during grading. Historical `handoff.json` records the pre-extension9-case state; this report and current manifests supersede its counts.

No active authoring jobs or fresh agent launches remain when this report is published. Main owns independent auditing, scorer calibration and agent launch.
