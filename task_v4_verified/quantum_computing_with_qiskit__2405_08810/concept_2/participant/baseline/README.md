# Weak exact baseline

`solve.py` reduces each target matrix to the identity by GF(2) row elimination,
reverses those row additions, and implements each nonlocal CX using a shortest
unweighted path. It moves the control using three-CX SWAPs, applies a local CX,
then restores every moved wire. It retains no free input/output permutation.

This implementation prioritizes exactness and a working artifact interface,
not count, duration or cancellation optimization. It is expected to exceed the
scientific caps. It does not use any evaluator data or a known feasible circuit.
Run it from any directory with `--output PATH`; its default input is resolved
relative to the participant package.
