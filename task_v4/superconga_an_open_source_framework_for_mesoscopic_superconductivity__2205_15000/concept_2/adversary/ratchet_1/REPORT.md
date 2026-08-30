# Measured champion ratchet

## Selected generation-2 proposal

Case: `u12_eta0.02_v6`; same 12x12 / 64-candidate / 24-inclusion complexity. Thresholds remain **0.96 core / 0.94 worst**.

This reruns the fresh generation-1 agent's preserved **construction/research algorithm** (`optimize.py` and `continuation.py`, captured before scratch cleanup), with the minimal adapter recorded in `adaptations.json`. The final generation-1 submission itself contained only `design.json`. This is NOT a static old-design/new-fingerprint comparison.

Completed blind portfolio: 9 runs, 17 scored stages, 2847 function evaluations, 558.64 aggregate optimizer wall-seconds / 558.54 process CPU-seconds; zero passing stages.

Best fabrication-valid score: core 0.06998741, worst 0.05857192; normalized RMSE 0.93001259. Witness official score: core 0.99999999999995, worst 0.99999999999994.

Public device: `adversary/ratchet_1/cases/u12_eta0.02_v6/public/input/device.json`

Public target: `adversary/ratchet_1/cases/u12_eta0.02_v6/public/input/target.npz`

Private witness: `adversary/ratchet_1/cases/u12_eta0.02_v6/private/design.json`

Frozen hashes, algorithm provenance, and thresholds: `proposal/freeze.json`.

## Completed sweep

Best scores include invalid projections when they outperform valid ones, so low scores are not merely fabrication/count rejection. Runtime is summed optimizer wall time, not elapsed batch time; raw errors are shown because scores clamp at zero.

| Case | Runs/stages | Best core | Best worst | RMSE | Valid best core | nfev | Optimizer s | CPU s |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| g1_control | 4/7 | 1.000000 | 1.000000 | 0.000000 | 1.000000 | 897 | 122.62 | 122.55 |
| u12_eta0.004_v1.65 | 4/6 | 1.000000 | 1.000000 | 0.000000 | 1.000000 | 1004 | 600.83 | 600.72 |
| u12_eta0.004_v3.2 | 3/3 | 0.000000 | 0.000000 | 1.745682 | 0.000000 | 600 | 398.54 | 398.42 |
| u12_eta0.004_v6 | 3/3 | 0.000000 | 0.000000 | 3.798063 | 0.000000 | 600 | 391.00 | 390.92 |
| u12_eta0.008_v1.65 | 3/3 | 1.000000 | 1.000000 | 0.000000 | 1.000000 | 586 | 230.92 | 230.89 |
| u12_eta0.008_v3.2 | 9/17 | 0.000000 | 0.000000 | 1.313154 | 0.000000 | 3139 | 1037.69 | 1037.45 |
| u12_eta0.008_v6 | 3/3 | 0.000000 | 0.000000 | 3.434609 | 0.000000 | 600 | 234.91 | 234.83 |
| u12_eta0.02_v1.65 | 3/3 | 1.000000 | 1.000000 | 0.000000 | 1.000000 | 345 | 69.50 | 69.49 |
| u12_eta0.02_v3.2 | 3/3 | 0.108251 | 0.027455 | 0.891749 | 0.108251 | 600 | 123.00 | 122.98 |
| u12_eta0.02_v6 | 9/17 | 0.069987 | 0.058572 | 0.930013 | 0.069987 | 2847 | 558.64 | 558.54 |
| u12_eta0.04_v1.65 | 3/3 | 1.000000 | 1.000000 | 0.000000 | 1.000000 | 265 | 36.16 | 36.16 |
| u12_eta0.04_v3.2 | 3/3 | 0.479632 | 0.441623 | 0.520368 | 0.479632 | 550 | 74.36 | 74.35 |
| u12_eta0.04_v6 | 6/14 | 0.195426 | 0.173430 | 0.804574 | 0.195426 | 1842 | 226.13 | 226.04 |
| u14_eta0.008_v3.2 | 3/3 | 0.000000 | 0.000000 | 1.495095 | 0.000000 | 600 | 371.35 | 371.27 |
| u16_eta0.004_v6 | 3/3 | 0.000000 | 0.000000 | 1.146117 | 0.000000 | 600 | 1194.68 | 1194.49 |

## Mechanism and validation

- Narrow-line cluster: at V=1.65 the same cavity is recovered by a direct start for eta=.008, .02, and .04, while eta=.004 defeats the tested direct starts. Extended CDF continuation recovers eta=.004 at V=1.65 (score 1.0), so sharp linewidth alone is not the selected ratchet mechanism.
- Strong-inclusion cluster: raising V at fixed geometry and linewidth creates poor relaxed basins and large binary-projection losses. The selected V=6, eta=.02 case also fails smooth, CDF, and binary continuation, including exact-count penalties; the best projected failure is fabrication-valid.
- Geometry-scale controls: 14x14 and 16x16 are measured separately; neither is needed for the proposed candidate.
- Candidate Jacobian condition numbers: witness 5028.5, uniform start 6773.6, best blind relaxed basin 2704.1.
- Candidate published grid: 61 uniform energies over [-.3,.3], spacing .01, eta=.02: four samples per Lorentzian FWHM. No adaptive peak selection or hidden frequency shift.
- Grid-refinement scores for the best blind pattern (same physical witness at each grid):
  - 61 energies: RMSE 0.93001259, core 0.06998741, worst 0.05857192.
  - 121 energies: RMSE 0.92851434, core 0.07148566, worst 0.06218805.
  - 241 energies: RMSE 0.92787216, core 0.07212784, worst 0.06237253.
- All 15 known witnesses independently verified: matrix equality, Hermiticity, particle-hole pairing, direct-resolvent LDOS, checker LDOS, and directional checks of both analytic Jacobians. Candidate original evaluator also verifies the witness and best blind pattern in a private mirror.
- Electron-hole mixed near-zero BdG modes and strong gap-off spectral changes are recorded in `private/diagnostics.json`; these support physical resonance/inclusion sensitivity, not a claim of self-consistent continuum Andreev physics.
- Oracle witness-local recovery passes, but is explicitly excluded from blind portfolio counts. The target is feasible and locally accessible.

No initial protected file changed. The generation-1 archives are separately hash-checked; concurrently added files outside the sidecar are listed rather than misreported as edits. No participant/evaluator/archive writes or fresh-agent launches were performed.

**Limitation:** these are finite multistart nonlinear inverse-design failures, not proof of hardness. The parent should launch the proposed completely fresh one-hour generation-2 attempt.
