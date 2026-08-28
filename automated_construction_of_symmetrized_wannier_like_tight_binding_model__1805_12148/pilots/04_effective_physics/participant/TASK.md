# Gauge-resolved low-energy models

Extend the supplied full-space model exporter into a reliable low-energy exporter. Recover an admissible standard basis and construct the Hermitian quasi-degenerate effective Hamiltonian through cubic order, together with its weak-field Zeeman tensor, from the supplied electronic-structure matrices.

Deliver `solve.py` in the attempt directory. It must accept `--input CASE.npz --output RESULT.npz`. The array contract and conventions are in `workspace/CONTRACT.md`; `workspace/legacy_export.py` is the projection-only starting point. Evaluation uses unseen bulk and monolayer calculations, target subspaces and equivalent coordinate/gauge conventions. Accuracy of basis recovery, remote-band corrections and magnetic response is scored separately. Use all supplied remote bands. NumPy and SciPy are available; no network or external reference packages are required. Each case has a 180-second, 8-GiB process budget with one BLAS thread.
