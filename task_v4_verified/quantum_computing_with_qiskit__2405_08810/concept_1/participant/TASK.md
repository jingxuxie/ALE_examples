# Hardware-aware phase compilation

Build a compiler for dense, correlated commuting Pauli-Z workloads on calibrated sparse quantum processors. Preserve every symbolic rotation exactly while reducing native two-qubit execution cost relative to the supplied compiler portfolio.

Assets: `input/FORMAT.md`, public workloads, a semantic/cost checker in `workspace/phase_model.py`, and an executable baseline in `baseline/solution.py`.

Interface: place `solution.py` and any supporting files in the submission directory. For each JSON workload supplied on stdin, emit one JSON circuit on stdout. The process serves multiple workloads; it must flush each response. The complete protocol and cost definition are in `input/FORMAT.md`.

Objective: all hidden workloads must be semantically valid. Achieve at least 82% mean cost reduction and at least 80% mean reduction in every workload family versus the frozen supplied baseline. This generation focuses on dense correlated rotations on 28-qubit lattice-like and chorded sparse devices, with 36–52 symbolic terms. `input/targets.json` records the fixed thresholds. Hidden workloads use the documented input ranges, not undisclosed instruction types.

Resources: one CPU core, 2 GiB memory, 15 seconds per workload including compilation, at most 100,000 output operations, and no network. Development time is one hour. Scoring reports mean reduction, worst-family reduction, semantic validity, and runtime compliance.
