# Compact coherent lookup synthesis

Construct exact shared XOR/AND networks for six nonlinear multi-output lookup
tables. Every row is supplied: this is compact circuit construction, not
prediction. Each circuit must satisfy its nonlinear-gate, multiplicative-depth,
affine-size and clean-workspace caps simultaneously.

The workload bank, executable baseline and exhaustive local checker are supplied.
The exact artifact and resource contracts are in `workspace/interface.md`.
Write `circuits.json` in your output directory. Evaluation reads only that static
JSON artifact and independently checks all rows and resource bounds. All six
instances must pass. Partial success is reported but does not pass the task.

You have one hour, four CPU threads and 8 GiB memory, with no network access.
The artifact limit is 8 MiB. Python, NumPy, SciPy and SymPy are available; no
quantum simulator or synthesis package is required. The tables are synthetic
structured coherent-data-loading workloads, not experimental data from the paper.
