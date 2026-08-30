# Provided native solver

The self-contained inference files are `solver.py`, `physics.py` and `hubbard.so`.
`hubbard.cpp` is the corresponding supplied source. Use the standard
`python3 solver.py REQUEST_JSON PREDICTIONS_JSON` interface. Active site counts
come from the input; no fixed-size buffer edits are needed for 10 or 12 sites.
The binary is a Linux x86_64 shared library; NumPy and the standard library are
the only Python dependencies. Keep all inference files together if copying to
`OUTPUT_DIR`. This asset is not a guarantee of resource or accuracy eligibility.
