# Scalar checkpoint execution

Implement accurate, efficient execution of the supplied scalar-flow checkpoints at their full lattice and feature sizes. Return vector fields, exact divergence, conditional coupling derivatives, transferred kernels, and forward/reverse density transport through the NPZ interface in `input/SPEC.md`.

Develop `workspace/solve.py` (`solve.py input.npz output.npz`). The starter is deliberately dense and incomplete. Checkpoint arrays, model contracts, and scoring details are in `input/`. Evaluation measures each numerical branch and end-to-end CPU runtime independently; do not substitute smaller models or stochastic traces.
