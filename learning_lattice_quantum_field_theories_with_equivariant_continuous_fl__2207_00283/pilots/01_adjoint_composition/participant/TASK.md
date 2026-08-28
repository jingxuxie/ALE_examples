# Differentiable Density Transport

Repair the supplied spectral and continuous transport implementation to produce accurate states, absolute log densities, and sensitivities for forward and inverse compositions.

Preserve `solve.py --input PATH --output PATH`. The complete contract is in `input/spec.md` and the workspace module docstring; `input/example.json` provides an unlabeled request. You may change or replace workspace code.

Evaluation separately measures states, endpoint-time, parameter and input gradients, densities, inverse branches, and deterministic sampling traces. Use CPU with at most four threads. No training or external data is required.

Submit `solve.py` with its required workspace files. The supplied runtime is `input/runtime/bin/python3.12`.
