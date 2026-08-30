# Frozen champion baseline

This is the independently runnable production snapshot of a successful earlier
solver, now evaluated on the larger weak-coupling regime in `input/CONTRACT.md`.
It is a comparison baseline, not a claimed passing solution for this generation.
Only production files are supplied; development logs, private cases, references,
and earlier evaluation feedback are withheld.

Run `python baseline/solve.py --request REQUEST.json --output STATE.npz` from
the participant directory. Each request carries its CPU and wall limits. The
baseline uses the same tensor format and physical Hamiltonian as every submission.
