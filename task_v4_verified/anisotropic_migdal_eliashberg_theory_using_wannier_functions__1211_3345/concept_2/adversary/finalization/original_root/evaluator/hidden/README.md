# Privileged calibration, not participant assets

The instance and target are frozen before initial participant launches. The fixed instance uses eight equal-DOS patches, three modes at 4/25/100 meV, total patch couplings 0.2–2.7, a fixed static diagonal of 0.4, and mode fractions 0.425/0.15/0.425. `provenance.json` records the deterministic feasible-array construction and hashes. A wide-band electronic scale of 20 eV gives a nominal largest `lambda Omega_max/E` of 0.0135; this is a model-scale check, not a lattice-stability proof.

Reproduce the private search with:

    OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python evaluator/hidden/curator_search.py --cpu-seconds 600 --seed 12113345

The script never overwrites an existing input dataset. It uses a 40-dimensional nullspace preserving every labeled mode row, diagonal, and full static aggregate. Entry-bound linear programs generate ascent/minimization directions, with line search for the minimizing endpoint. It stops after 80 deterministic multistarts or the CPU limit, whichever is first. There is no need to exhaust ten minutes when those restarts already saturate the observed solution and exceed the target. `search.jsonl` records every restart; `search_state.npz` saves coordinates and basis. Reruns append a new start event and may overwrite private witness files, never public constraints or target.

Run `python evaluator/hidden/validation.py`, then `python evaluator/hidden/finalize.py` to independently audit the saved witness and refresh status/curator copies. The initial baseline result must already exist; reproduce it with the public baseline and evaluator commands in their READMEs. Verification includes all published families and 96/192 grids, nominal 384, full independently assembled signed-frequency comparisons, and the regular-row control. Floating point reproduction should be judged numerically, not by NPZ timestamps or CPU-time log fields.

No global optimum or interval-certified infinite-cutoff error bound is claimed. The target is a witnessed falsification threshold, not a supremum claim. The parent handles isolation, immutable evaluator staging, and tournament runners.
