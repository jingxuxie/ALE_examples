# Biased Pauli recovery

Build a decoder that transfers across sparse quantum memory codes and known
local coordinate frames under biased, correlated Pauli noise. Return a
syndrome-consistent correction that preserves the encoded state, not merely
a low-weight solution of the parity equations.

Implement `workspace/solve.py --input case.npz --output answer.npz`.
The complete mathematical contract, file schema, and resource limits are in
`input/FORMAT.md`. `workspace/solve.py` is an independent-marginal starting
point. The supplied matrices and unlabelled examples are for structural
checks only; hidden evaluation covers both block sizes, different Clifford
frames, and shifted noise biases. Improve the decoder, not the file format.

Use only the released files and the participant Python environment. NumPy,
SciPy, g++, and the original native BP+OSD sources in `workspace/legacy_2020/`
are available. Build on those sources if useful: the new work is frame and
correlation transfer, not reinventing binary decoding. No specialized Python
decoder packages or working Numba are provided. Do not install or retrieve
external solvers. Submit the workspace
directory containing `solve.py` and any supporting files.
