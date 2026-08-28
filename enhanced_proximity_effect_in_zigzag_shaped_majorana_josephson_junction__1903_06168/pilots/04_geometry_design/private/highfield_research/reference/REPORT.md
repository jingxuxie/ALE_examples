# Narrowed-high-field fixed-reference calibration

private narrowed-high-field adaptation diagnostic; no initial score, acceptance change, or demonstrated solver capability gap.

Strong is exact archived homogeneous_filtered.p epoch 800; weak is the unchanged original zigzag. Source-member hashes and array equality verified. No geometry edits.

Physical grid: 61×65 sites; 15,860 DOF; spacing 20.0 nm.

Scenario order (mu_normal, EZ), meV: 0: (10.3, 1.47); 1: (12.6, 1.45); 2: (14.8, 1.48).

| Design | Scenario | Full-51 gap (meV) | Independent Q | Wall seconds |
|---|---|---|---|---|
| weak | 0 | 0.078047293445 | -1 | 94.94 |
| weak | 1 | 0.077256313928 | -1 | 96.76 |
| weak | 2 | 0.073281819759 | -1 | 99.27 |
| strong | 0 | 0.222953827359 | -1 | 120.00 |
| strong | 1 | 0.225324681818 | -1 | 144.13 |
| strong | 2 | 0.188049606905 | -1 | 127.75 |

- weak: R=0.07473848106825232 meV; physical_feasibility=True; complete=True.
- strong: R=0.2000794894660748 meV; physical_feasibility=True; complete=True.
- Unbounded anchors ready: True; strong-minus-weak=0.12534100839782247 meV.
- Numerical wall time: 144.85 seconds of 600; six one-thread workers on [40, 42, 44, 46, 48, 50].
- Stored-output validation passed: True; incomplete values are not failures.

R = 0.5 mean(scenario gaps) + 0.5 minimum(scenario gaps). Feasibility includes unchanged manufacturing, all three independent Q=-1, and each full-51 gap > 1e-5 meV.

This is a fixed-reference calibration, not a comparison with the adapted submitted solver. The broad-region output's high-field tradeoff is insufficient by itself to establish hardness. Main owns the adaptation run and subsequent interpretation; no initial scoring or public files are changed.

Full arrays and metadata: calibration.json and measurements/. Source/input/helper hashes: fingerprint.json. No optimizer or submitted geometry is executed here.
