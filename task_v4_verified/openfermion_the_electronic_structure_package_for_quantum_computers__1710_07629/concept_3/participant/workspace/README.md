# Read-only workspace assets

This directory is not writable in the participant runner. Put `solver.py` and
all inference artifacts under the supplied `OUTPUT_DIR`, not in this tree.
Do not delete or overwrite `audit_isolation.py`; it is a preserved launcher audit.
Inference writes belong only in `TMPDIR`; the submitted directory is then read-only too.
