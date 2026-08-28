# Finite-system quantum spectroscopy

Implement `solve.py --input INPUT.json --output OUTPUT.json` for the three model families specified in `input/CONTRACT.md`.

Return the finite-system ground energy in the requested conserved sector, the specified sector gap, and every requested correlation. Systems are too large for the supplied small exact-diagonalization baseline. Energy, gaps, and different correlation types are scored independently; energy alone is insufficient.

Start from `workspace/solve.py`, or replace it. Submit a directory containing `solve.py` and any supporting files. Only NumPy, SciPy, and the Python standard library are guaranteed. No network or external solver installation is available during evaluation. Each case has a 600-second wall-clock limit; within that limit runtime does not affect the numerical score. Target at most 8 GiB and four CPU threads per case.

The two examples are unlabeled interface examples, not the evaluation set. Hidden cases use the same contract and physical parameter ranges, with different sizes, couplings, and measurements.
