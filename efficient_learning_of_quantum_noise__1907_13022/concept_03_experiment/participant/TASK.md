# Recover correlated calibration noise

Complete the analysis pipeline for simultaneous randomized-circuit calibration records. Recover a SPAM-robust, normalized one-cycle effective error distribution and quantify conditional dependence and the discrepancy of the supplied spatial model.

Submit a self-contained `solver.py` in your output directory. It must run as `python solver.py INPUT.npz OUTPUT.npz`; only this file and the current input are staged for evaluation. The numerical contract is in `input/FORMAT.md`; `workspace/baseline.py` is an intentionally weak starting point. Evaluation uses unseen real acquisition records, including single- and simultaneous two-qubit operation, and scores channel reconstruction and dependency diagnostics separately. Allow 120 seconds and 3 GiB per record. NumPy and SciPy are installed.
