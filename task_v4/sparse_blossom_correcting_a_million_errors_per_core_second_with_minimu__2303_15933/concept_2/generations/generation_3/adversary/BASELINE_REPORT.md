# Independently evaluated actual champion

Artifact: `participant/baseline/champion.json`, byte-identical to the promoted
generation-two v1 witness. Both previous fresh attempts officially passed; v1
won on score 1.0104109012101703 versus v2's 1.0104079400244192.

The full independent 5,791-point positive/min-plus DP gives:

- Valid artifact, scientific failure; standardized reason `calibration_targets_not_met`.
- Core score 0.9197899012060603; inherited-generation-two score 1.0104109012101703.
- New certified gap 0.7818214160251512, posterior 0.8369618827942639, mass 0.00001853306134534733.
- Actual anchor minima: gap 0.8053940642086896, posterior 0.8418515011072247, mass 0.000019270660798792905.
- Nine genuinely failing new paths: two with both gap and posterior failures, six posterior-only, one gap-only.
- Five additional certificate-only failures; no sampled syndrome-mass failure.
- CPU 887.024658039 seconds, wall 959.688448546 seconds, peak RSS 68.84375 MiB.

These metric minima need not occur on the same path or at the same point.
Detailed records are in `baseline_independent_metrics.json`. The audit independently
compares every native anchor against the public frontier recurrence, tests 258
off-anchor points and 129 reflection-domain controls, checks the slower generic
NumPy recurrence and edge-order invariance, and rejects forty malformed artifacts
through both validators. No matching package or privileged reference solution
enters evaluation. No runtime or wall-contended host failure is used as evidence.
