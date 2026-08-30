# Deliberately inefficient baseline

Run `python3 baseline/synthesize.py --output workspace/submission/witness.json`
from the participant directory. Python 3.10+ and only the standard library are
needed. `--input` can select an explicit suite file.

Each required parity is independently computed from the identity basis and
uncomputed. A Gauss–Jordan elimination of the target is then reversed to produce
the final map. Every remote CNOT is implemented by moving its control along a
shortest path with native three-CNOT SWAPs, applying the CNOT, and restoring the
intermediate wires. Thus all hardware and algebra constraints are satisfied,
but no useful parity sharing or joint count/depth optimization is attempted.
The final phase-synthesis problem remains even if you replace the final linear
synthesis routine with a better one.
