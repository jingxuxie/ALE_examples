# Author-only late-time reference

`solver.py` implements the unchanged c04 `solve(case)->dict` API. `engine.py` is a
byte-identical execution copy of the frozen parent engine, staged by the probe
orchestrator; it is not edited. `accelerated.py` changes only propagation.

The exact nonzero graph of the energy-basis dissipator partitions Liouville space.
For each component, the independent `centered_expm` method exponentiates the full
block after subtracting a scalar imaginary frequency, then restores that phase.
The default `commuting_eigh` method diagonalizes the Hermitian dissipative block
and applies the coherent phases separately. It refuses cases whose measured
commutator/Hermiticity time indicators exceed its guard thresholds. No additional
off-block couplings are discarded, and trace/Hermiticity/positivity are checked.

Validation and actual 60-second-worker isolated runs are under task-root
`authoring/c04_longtime_probe/`. The reference is a new benchmark-author numerical
implementation of the existing secular structure, not official paper code.
It is not installed into the original frozen reference or any participant tree.
