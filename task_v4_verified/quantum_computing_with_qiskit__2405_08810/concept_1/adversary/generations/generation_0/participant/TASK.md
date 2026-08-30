# Hardware-aware phase compilation

Build a compiler for commuting Pauli-Z rotations on a calibrated sparse quantum processor. Preserve every symbolic rotation exactly while reducing native two-qubit execution cost relative to the supplied compiler portfolio.

Assets: `input/FORMAT.md`, public workloads, a semantic/cost checker in `workspace/phase_model.py`, and an executable baseline in `baseline/solution.py`.

Interface: place `solution.py` and any supporting files in the submission directory. For each JSON workload supplied on stdin, emit one JSON circuit on stdout. The process serves multiple workloads; it must flush each response. The complete protocol and cost definition are in `input/FORMAT.md`.

Objective: all hidden workloads must be semantically valid. Achieve at least 40% mean cost reduction and at least 25% mean reduction in every workload family versus the frozen supplied baseline. Families include local lattices, bottlenecked devices, heterogeneous calibrations, and shared dense parities. Hidden workloads use the documented input ranges, not undisclosed instruction types.

Resources: one CPU core, 2 GiB memory, 15 seconds per workload including compilation, at most 100,000 output operations, and no network. Development time is one hour. Scoring reports mean reduction, worst-family reduction, semantic validity, and runtime compliance.
