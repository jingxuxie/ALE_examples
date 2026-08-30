# Falsify a calibration screen under independent phase drift

You are auditing a quantum-control team's claim that its compressed calibration screen certifies a qubit model for same-depth application circuits. Construct a physically valid coherent-leakage counterexample that remains a counterexample under the disclosed independent gate-phase tolerances: calibration accepts, but an application circuit has a large prediction error and little final leakage.

Assets: the exact processor family, reported CPTP model, calibration circuits, and tolerance scenarios in `input/`; a NumPy simulator in `workspace/screen.py`; and the previous-generation champion in `baseline/witness.json`. That champion is a runnable starting point, not a passing solution for this generation. This challenges the supplied screen's sufficiency, not a GST theorem.

Submit **one static `witness.json`** in the designated output directory. The complete interface is in `input/INTERFACE.md`. Run `python workspace/screen.py --witness PATH` for local measurements or `python baseline/search.py --output PATH` to emit the baseline. Submitted code is never executed by the evaluator.

A passing witness satisfies every calibration and held-out bound in **all 21 enumerated tolerance scenarios**, including the original common-mode scenarios and independent phase corners. The circuit has exactly 64 gates. Scores report nominal and worst-scenario prediction error plus constraint violations. All scientific acceptance criteria are public; probabilities are independently reproduced by the private evaluator.

Budget: one hour, four CPU cores, 4 GiB address space per process, no network. The JSON file is limited to 32 KiB. No report is required.
