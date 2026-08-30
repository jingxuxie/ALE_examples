# Private generation-2 portfolio provenance

This directory is a generation-privileged sidecar, not participant material.
The participant, evaluator, thresholds, and target list remain frozen.
No fresh v5/v6 attempt tensor, construction source, or log is accessed.

Permitted local sources inspected and reused:

- `../portfolio_g1/optimize.py`: real parity-block QR parameterization,
  symmetric-sector transfer contractions, stationary-density solve, dyadic
  powers, Torch differentiation, and bounded L-BFGS optimization. Its source
  is copied here as `optimize.py`; only its local utility definitions are
  imported by the new `fit.py` entry point.
- `../../champions/generation_2/optimize.py`: generation-privileged champion
  construction source, specifically its stationary-density inverse-power
  parameter preconditioning. The champion tensor is a warm start, not a v3
  solution and not evidence of independent fresh-agent capability.
- `../../evaluator/hidden/trusted_physics.py`: the unmodified frozen v3
  targets, literal submitted-state subtraction, admissibility checks, and
  full numerical scoring. This remains the authority.
- `../ratchet_2/freeze_manifest.json`: immutable participant/evaluator hashes.

The new fitter evaluates every required two-point separation and all sixty
composite quartets on one actual tensor. During differentiation the right
interval environment is centered by the submitted state's own pair mean.
This is algebraically the same covariance as literal raw XXXX minus the
product of the submitted means; numerical agreement is independently
checked against the frozen literal-subtraction implementation.

The portfolio uses additional generation-time compute and prior source
reuse, so it is not an hour-budget participant attempt or evidence about
fresh-agent discoverability. Only an actual NPZ with a full unmodified
`evaluate.py` pass can demonstrate achievability of this frozen contract.
