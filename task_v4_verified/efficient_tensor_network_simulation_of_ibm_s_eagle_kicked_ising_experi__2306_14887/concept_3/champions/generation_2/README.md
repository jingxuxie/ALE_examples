# Final control witness

`pulses.json` is the submission: schema version 1, with 24 pairs of kick
angles in radians. The checker needs only this file.

Validation records:

- `public_score.json`: all 31 public scenarios, using the provided scoring CLI.
- `validation.json`: exact public-simulator checks of public scenarios, the
  generated stress pool, and 4,096 independently generated scenarios, including
  state norms and zero-drift global-X parity. It records the artifact SHA-256.
- `field_scan_validation.json`: 32,768 drift-sign-corner checks at 16 selected
  calibrations, with the worst cases cross-checked against the public simulator.
- `adversarial_validation.json`: the expanded stress pool after 2,048 random
  adversarial starts plus 48 worst-case warm starts.

The remaining scripts, logs, and checkpoints support the control search and
validation; none is required or executed by the submission checker.

Final recorded minima:

| Validation set | Cases | Minimum fidelity |
| --- | ---: | ---: |
| Public | 31 | 0.9831393255745452 |
| Generated stress | 5,489 | 0.9518778777128671 |
| Independent random | 4,096 | 0.9545214538248055 |
| Drift-sign scan | 32,768 | 0.9518778777128682 |

The largest norm deviation in the public-simulator validation is
1.0436096431476471e-14.

The private 223-scenario suite was not available. These finite checks are not
a certificate for the continuous uncertainty family or a claimed private result.
