# Published-scale reference calibration

Out-of-initial-contract private audit only. No submitted solver measurement or initial score/acceptance change.

Source: `code/data/homogeneous_filtered_1940.p`, exact epoch 800; 66×97 sites, 25,608 DOF. Archive array equality and source hashes verified.

Full 51-momentum gap in meV, independent Pfaffian Q; all source masks and physical constraints unchanged.

| Design | Scenario | Gap (meV) | Q | Wall seconds |
|---|---|---|---|---|
| weak | 0 | 0.091683719214 | -1 | 198.33 |
| weak | 1 | 0.088038531593 | -1 | 196.81 |
| weak | 2 | 0.070065906906 | -1 | 198.56 |
| strong | 0 | 0.150539774454 | -1 | 363.95 |
| strong | 1 | 0.226919124309 | -1 | 386.61 |
| strong | 2 | 0.225052404281 | -1 | 330.71 |

- weak: R=0.07666431307202659 meV; physical_feasibility=True; complete=True.
- strong: R=0.17568843773472642 meV; physical_feasibility=True; complete=True.
- Normalization anchors ready: True; strong-minus-weak=0.09902412466269983 meV; no clipping.
- Numerical wall time: 387.90 seconds of 900; six one-thread workers on [16, 18, 20, 22, 24, 26].
- Output validation passed: True. Incomplete values are not physical failures.

R = 0.5 mean(scenario gaps) + 0.5 minimum(scenario gaps). Manufacturing is checked independently; all three Q must be -1 and full-grid gaps must exceed 1e-5 meV.

`calibration.json` stores complete aggregate and per-scenario records. `measurements/` includes all eight energies per momentum, gap curves, Q, checkpoint timings and resource metadata. `fingerprint.json` records source/input/helper hashes. No optimization or wavefunction archive is created.
