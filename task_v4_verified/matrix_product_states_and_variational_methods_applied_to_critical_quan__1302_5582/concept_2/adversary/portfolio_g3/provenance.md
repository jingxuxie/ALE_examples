# Private v4 achievability portfolio

This generation-privileged portfolio writes only in this directory. No v7/v8
attempt, audit, or log is read, and no participant/evaluator file is modified.

Permitted source inspection/reuse:

- `../../champions/generation_3/optimize.py`: v6's real parity-sector QR
  parameterization and inserted-transfer propagation; read as construction
  provenance, not executed in its archived location.
- `../../champions/generation_3/state.npz`: the sole warm-start tensor.
- `../portfolio_g2/fit.py` and `optimize.py`: copied here and extended with
  differentiable three-composite cumulants and six-family scoring.
- `../../evaluator/hidden/trusted_physics.py`: immutable v4 authority,
  including actual left/right fixed-point normalization.

At most three single-thread warm-start variants are used, with different
static stationary-density preconditioners. Their QR tensors are right
canonical to roundoff. The differentiable centered K3 contractions are
checked against literal full-tensor, actual-L/R normalized frozen values.
Only an actual `evaluate.py` pass on the saved NPZ can establish achievability.
A successful full evaluation creates a stop marker for all private workers.

Extra compute and previous-source reuse are generation-time asymmetries,
not evidence of independent fresh-agent performance. Construction source
and private outputs are never placed into the participant surface.
