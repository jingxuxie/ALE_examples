# Recover an analog quantum memory

Implement `workspace/solve.py` to recover the final logical state and reconstruct
the noiseless parity history of a quantum memory from calibrated, noisy readouts.

Run as `python solve.py --input CASE.npz --output ANSWER.npz`.
The complete model, array schema, consistency rules, resources and scoring
objectives are in `input/FORMAT.md`. The small example is unlabeled.

Reusable binary-decoding components are provided in `workspace/`; the task is
their integration with continuous evidence and temporal/check consistency.
Do not rely on network access or files outside the supplied task and submission.
