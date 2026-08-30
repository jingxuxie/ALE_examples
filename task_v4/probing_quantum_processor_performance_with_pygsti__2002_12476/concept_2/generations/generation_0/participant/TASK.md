# Falsify a compressed processor-model acceptance screen

You are auditing a quantum-control team's claim that its compressed calibration screen is sufficient to certify a qubit model for same-depth application circuits. Produce a physically valid, reproducible counterexample with coherent leakage: the screen accepts, but a held-out circuit has a large prediction error despite little population remaining outside the qubit.

Assets: `input/specification.json`, `input/calibration.json`, `input/INTERFACE.md`, a NumPy simulator and acceptance screen in `workspace/screen.py`, and a runnable weak search in `baseline/search.py`. The exact processor family, reported CPTP model, calibration circuits, tolerance scenarios, and thresholds are public. This is a challenge to the supplied sufficiency claim, not to a GST theorem.

Submit **one static `witness.json`** in the designated output directory. Its interface is specified in `input/INTERFACE.md`. Run `python workspace/screen.py --witness PATH` for local measurements or `python baseline/search.py --output PATH` for a baseline. The private evaluator independently reproduces all probabilities; submitted code is never executed.

A passing witness satisfies every calibration bound and every held-out bound in **all five tolerance scenarios**. Scores report nominal prediction error, worst-scenario prediction error, and constraint violations. Calibration and held-out circuits have comparable depth; the held-out circuit is exactly 64 gates. Search budget: one hour, four CPU cores, 4 GiB address space per process, no network. The JSON file is limited to 32 KiB. No report is required.
