# Builder-only validation

Run `PYTHONDONTWRITEBYTECODE=1 python3 adversary/validate.py` from the concept root.
The suite independently tests Fock-space parity, determinant overlap, orbital
gauge invariance, wrong-state and budget failures, malformed JSON, nonfinite
numbers, nonedges, overlapping layers, symlinks/FIFOs, and parser limits.
Fixtures and numerical details here are private, not participant assets.
