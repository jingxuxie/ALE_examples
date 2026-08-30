# Calibration-aware architecture-retargetable routing

Build a routing engine for opaque two-qubit programs on calibrated hardware graphs. Preserve every logical operation and its wire dependencies while minimizing calibrated two-qubit work and execution depth. Edge calibrations and the fixed initial placement are provided in each input.

Submit a self-contained directory containing `solve.py` and any supporting files. Each invocation receives one JSON instance on standard input and must emit one JSON route on standard output. Only the submission, system runtime, and current input are accessible during evaluation.

Assets: the original four-configuration reference router in `baseline/solve.py`, twelve public examples in `input/`, their reference scores, and the exact interface in `input/FORMAT.md`. Example invocation: `python3 baseline/solve.py < input/public_g2_chain_0.json`.

The fixed targets are at least **40% geometric-mean cost reduction overall** and at least **30% reduction in each architecture family**, relative to the supplied reference router. Every route must be valid. Hidden evaluation contains 36 instances, six each from chain, ring, grid, ladder, tree, and modular architectures. Public and hidden examples share the disclosed dimensions and workload mechanisms.

Resources: **one CPU, 2 GiB address space, 12 seconds per instance including startup, 360 seconds for the 36-instance suite, 128 MiB of submission files**, and no network or external quantum compiler. Quality, family quality, validity, and resources are evaluated separately. The final logical-to-physical permutation is unrestricted.
