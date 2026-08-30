# Private calibration and frozen suite

Do not release this directory to participants. `cases.json` and the public scoring
specification are frozen before any solver launch. `calibrate.py` will retain
baseline outputs, cap-limited reference MPS, recomputed energies, solver settings,
timings, and hashes. Reference values are attainable variational **upper** energies,
not alleged exact ground energies. Targets are not adjusted after calibration.

The eight deliberately finite chains cover four equal-weight families and different
oscillator conditioning, local truncations, parity constraints, and spatial profiles.
"Crossover" is a family label for finite systems, not a claim of a thermodynamic
critical point. Public full tensor machinery makes this a budget-allocation,
initialization, sector, and convergence problem rather than library reproduction.
