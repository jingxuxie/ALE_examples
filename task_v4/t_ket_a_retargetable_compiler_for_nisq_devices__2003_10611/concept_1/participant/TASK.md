# Calibration-weighted qubit routing

Deliver a better architecture-retargetable routing engine for opaque two-qubit quantum programs. Preserve every logical operation and each wire's order while reducing calibrated native-gate cost and depth.

Assets include a runnable multi-configuration router, exact public route validation, and representative architecture/workload instances. The input and output contract is in `input/FORMAT.md`.

Submit `solve.py` and any supporting files in your output directory. Each invocation, `python3 solve.py`, receives one JSON instance on standard input and emits one JSON routing result on standard output. The submission must be self-contained; only the submitted directory, system runtime, and input are available during scoring.

The fixed target is at least **15% geometric-mean cost reduction** against the supplied portfolio and at least **8% reduction in every architecture family**, with every route valid. Hidden tests cover the six disclosed families and dimensions. The cost combines calibrated two-qubit work and two-qubit depth; no hardware calibration labels are hidden from an invocation.

Limits: one CPU, 2 GiB address space, 8 seconds per instance including startup, 240 seconds for the 36-instance suite, 128 MiB submitted files, no network or external quantum compiler. You have one hour to develop the submission. Quality, worst-family quality, validity, and runtime are scored separately.
