# Working search scaffold

Run `python solve.py --output witness.npz`, then `python check.py witness.npz`.

The initial implementation intentionally returns the reference twice. Use `physics.load_instance`, `constraint_report`, and `EliashbergSolver` while developing a search. `eigenpair(..., gradient=True)` returns the matrix-entry gradient at fixed normal-state rows, suitable only for directions preserving those rows. It also returns the critical eigenvector in gap coordinates. All target/refinement settings are public in `../input/config.json`.

The evaluation entry point is outside this participant directory. It consumes only the final NPZ artifact. A public check never claims the independent audit has run.
