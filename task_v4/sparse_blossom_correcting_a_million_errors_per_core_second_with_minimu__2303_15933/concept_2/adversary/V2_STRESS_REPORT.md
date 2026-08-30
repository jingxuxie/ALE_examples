# Private local-calibration stress report

NOT a new task generation or a frozen ratchet. Never expose this sidecar to running agents.

The input is validated once as a nominal design. Calibrated rates are not clipped back to design bounds: that would erase calibration error.
Every nontrivial profile preserves the total expected error count exactly up to floating-point roundoff. Thus these failures are not disguised global noise increases.
Detector IDs and logical cut stay fixed during calibration. Graph automorphisms are separate invariance controls, not physical adversaries.

## Lowest exact metrics

- gap: `detector_corners/50@0.050`, alpha=1.050; exact gap=0.808527135944, opposite posterior=0.891220296208, mass=2.50115866791e-05. TARGET VIOLATED.
- posterior: `detector_corners/102@0.050`, alpha=0.950; exact gap=1.32222420608, opposite posterior=0.838724993107, mass=1.90703774702e-05. TARGET VIOLATED.
- mass: `detector_corners/3@0.050`, alpha=0.950; exact gap=1.24378525949, opposite posterior=0.853830110582, mass=1.81501506278e-05. target still met at all anchors.

## Family failure clusters

Counts are suite entries, sometimes repeated across families, not estimated calibration-failure probabilities.

| Family @ amplitude | Cases | Actual anchor failures | Certificate-only failures |
|---|---:|---|---:|
| row_corners@0.020 | 14 | {"lost_gap": 3, "none": 11} | 10 |
| column_corners@0.020 | 30 | {"none": 30} | 30 |
| quadrant_corners@0.020 | 14 | {"lost_gap": 1, "none": 13} | 12 |
| local_2x2_patch@0.020 | 24 | {"none": 24} | 20 |
| detector_corners@0.020 | 128 | {"lost_gap": 6, "none": 122} | 121 |
| smooth_fields@0.020 | 128 | {"none": 128} | 125 |
| row_corners@0.050 | 14 | {"lost_gap": 7, "lost_posterior": 3, "none": 4} | 4 |
| column_corners@0.050 | 30 | {"lost_gap": 8, "lost_posterior": 3, "none": 19} | 19 |
| quadrant_corners@0.050 | 14 | {"lost_gap": 6, "lost_posterior": 1, "none": 7} | 7 |
| local_2x2_patch@0.050 | 24 | {"lost_gap": 8, "lost_posterior": 2, "none": 14} | 13 |
| detector_corners@0.050 | 128 | {"lost_gap": 70, "lost_posterior": 10, "none": 48} | 48 |
| smooth_fields@0.050 | 128 | {"lost_gap": 42, "lost_posterior": 4, "none": 82} | 82 |

## Interpretation and continuation

An exact anchor below a target is a genuine physical failure of that proposed extension. A failed lower-bound certificate alone does not establish a physical failure.
The original frozen task remains satisfied or not according to its unchanged nominal checker; local calibration is additional, currently unscored stress.
Actual anchor-failure counts: {"lost_gap": 151, "lost_mass": 0, "lost_posterior": 23}. All profiles still certify the basic entropy inversion throughout the global interval: True.
All reported interval bounds cover the global alpha interval for each listed local profile. Corner profiles do NOT certify the continuum of local fields; no extremum-at-corners theorem is assumed.

At local amplitude 0.020, known-input certified lower bounds across the finite suite are gap=0.932898129675, posterior=0.840824230204, mass=1.70852060064e-05.
At local amplitude 0.050, known-input certified lower bounds across the finite suite are gap=0.697901125877, posterior=0.82319705009, mass=1.6249384522e-05.

A plausible continuation retains every original nominal target and adds explicitly declared local-calibration profiles with separate guard margins. The bounds above supply a known feasible envelope for this input, not thresholds to freeze automatically. Test the actual champion first; no new generation or secret condition is created here.
There is no new optimized design witness in this sidecar. Whether the original strict targets can survive a whole independent local-calibration box remains unproved.

## Integrity controls

- 6 reflection controls pass, including odd-syndrome logical-class XOR under left/right exchange.
- 6 generic 2**21-state checks were run, including reordered edge processing: True.
- Frozen participant/evaluator manifest hashes match before and after; no status writes or fresh runner calls occur.
- Exact means exhaustive positive DP and min-plus inference in binary64, not sampling or a rational-arithmetic claim.
