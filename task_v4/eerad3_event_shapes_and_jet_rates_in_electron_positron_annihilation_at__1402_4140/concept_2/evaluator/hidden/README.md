# Evaluator-only trust boundary

`trusted_shapes.py` is a scalar standard-library implementation independently
organized around the official singleton/pair thrust construction, tensor minors
and list-based E-scheme clustering. It imports no participant module or mutable
participant contract. `evaluate.py` owns the frozen thresholds. Cross-checks
against compiled release and v1 sources belong to generation validation only;
evaluation needs neither a compiler nor NumPy nor external files.

Ship only `participant/` to the solver. Keep evaluator, attempts, champions,
adversary and status private. Hidden means withheld by packaging, not a claim of
OS isolation on the builder's shared filesystem.
