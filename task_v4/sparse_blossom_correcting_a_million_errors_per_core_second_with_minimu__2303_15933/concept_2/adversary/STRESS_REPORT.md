# Private local-calibration stress report

NOT a new task generation or a frozen ratchet. Never expose this sidecar to running agents.

The input is validated once as a nominal design. Calibrated rates are not clipped back to design bounds: that would erase calibration error.
Every nontrivial profile preserves the total expected error count exactly up to floating-point roundoff. Thus these failures are not disguised global noise increases.
Detector IDs and logical cut stay fixed during calibration. Graph automorphisms are separate invariance controls, not physical adversaries.

## Lowest exact metrics

- gap: `detector_corners/68@0.050`, alpha=1.050; exact gap=0.814943376968, opposite posterior=0.886996248818, mass=2.79080896858e-05. TARGET VIOLATED.
- posterior: `row_corners/5@0.050`, alpha=0.950; exact gap=1.2993897912, opposite posterior=0.850205305076, mass=1.99152771948e-05. target still met at all anchors.
- mass: `detector_corners/107@0.050`, alpha=0.950; exact gap=1.05329049101, opposite posterior=0.877018412888, mass=1.85670949187e-05. target still met at all anchors.

## Family failure clusters

Counts are suite entries, sometimes repeated across families, not estimated calibration-failure probabilities.

| Family @ amplitude | Cases | Actual anchor failures | Certificate-only failures |
|---|---:|---|---:|
| row_corners@0.020 | 14 | {"lost_gap": 2, "none": 12} | 9 |
| column_corners@0.020 | 30 | {"none": 30} | 17 |
| quadrant_corners@0.020 | 14 | {"none": 14} | 10 |
| local_2x2_patch@0.020 | 24 | {"none": 24} | 13 |
| detector_corners@0.020 | 128 | {"lost_gap": 3, "none": 125} | 105 |
| smooth_fields@0.020 | 128 | {"none": 128} | 100 |
| row_corners@0.050 | 14 | {"lost_gap": 6, "none": 8} | 7 |
| column_corners@0.050 | 30 | {"lost_gap": 5, "none": 25} | 21 |
| quadrant_corners@0.050 | 14 | {"lost_gap": 3, "none": 11} | 11 |
| local_2x2_patch@0.050 | 24 | {"lost_gap": 3, "none": 21} | 17 |
| detector_corners@0.050 | 128 | {"lost_gap": 71, "none": 57} | 55 |
| smooth_fields@0.050 | 128 | {"lost_gap": 34, "none": 94} | 80 |

## Interpretation and continuation

An exact anchor below a target is a genuine physical failure of that proposed extension. A failed lower-bound certificate alone does not establish a physical failure.
The original frozen task remains satisfied or not according to its unchanged nominal checker; local calibration is additional, currently unscored stress.
Actual anchor-failure counts: {"lost_gap": 127, "lost_mass": 0, "lost_posterior": 0}. All profiles still certify the basic entropy inversion throughout the global interval: True.
All reported interval bounds cover the global alpha interval for each listed local profile. Corner profiles do NOT certify the continuum of local fields; no extremum-at-corners theorem is assumed.

At local amplitude 0.020, known-input certified lower bounds across the finite suite are gap=0.9358544332, posterior=0.849647667782, mass=1.73977264598e-05.
At local amplitude 0.050, known-input certified lower bounds across the finite suite are gap=0.704893489858, posterior=0.83564428294, mass=1.66322934974e-05.

A plausible continuation retains every original nominal target and adds explicitly declared local-calibration profiles with separate guard margins. The bounds above supply a known feasible envelope for this input, not thresholds to freeze automatically. Test the actual champion first; no new generation or secret condition is created here.
There is no new optimized design witness in this sidecar. Whether the original strict targets can survive a whole independent local-calibration box remains unproved.

## Integrity controls

- 6 reflection controls pass, including odd-syndrome logical-class XOR under left/right exchange.
- 6 generic 2**21-state checks were run, including reordered edge processing: True.
- Frozen participant/evaluator manifest hashes match before and after; no status writes or fresh runner calls occur.
- Exact means exhaustive positive DP and min-plus inference in binary64, not sampling or a rational-arithmetic claim.
