# Adaptive cross-resonance calibration

Calibrate the five signed coefficients of a two-qubit cross-resonance Hamiltonian from a limited sequence of experiments. Your calibration controller chooses product-state preparations, Pauli measurements, evolution times, and shot allocations, observing only sampled binary counts. State-preparation, readout, and decoherence parameters are unknown nuisance variables.

Submit a directory containing `solution.py`, an executable Python line-JSON controller. It receives one episode on standard input, requests experiments on standard output, and returns one parameter estimate. Every hidden episode runs in a new isolated process. No Qiskit installation is needed; NumPy and SciPy are available.

The exact forward model, parameter families, protocol, scoring, and standalone development harness are in `input/`. A runnable fixed-schedule baseline is in `baseline/`. You may use the public assets but cannot access evaluator files, hidden seeds, or other episodes.

Each episode allows **24,576 shots, 192 queries, times in [0, 12], 20 solver wall seconds, 18 CPU seconds, and 1 GiB address space**. Solver time includes imports and interaction but excludes trusted sandbox creation. Recovery is scored by normalized coefficient error, with both overall and worst-family targets specified in `input/config.json`. All episodes must be protocol-valid. Only the five Hamiltonian coefficients are scored; nuisance estimates are optional.

This is a synthetic active-design extension motivated by partial-ZX retargeting and calibration, not a reproduction of the paper's experiment. Details and provenance: `input/MODEL.md` and `input/SOURCES.md`.
