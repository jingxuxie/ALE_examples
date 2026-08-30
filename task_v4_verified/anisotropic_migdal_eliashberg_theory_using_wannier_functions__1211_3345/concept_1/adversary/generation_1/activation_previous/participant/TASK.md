# Branch-correct anisotropic Eliashberg solver

Improve the supplied nonlinear imaginary-axis solver. Recover the nonzero,
low-frequency same-sign superconducting branch across multiband, separated
phonon-scale, nearly critical, weak-interband, and combined cases. The physics
operators and derivative interface are supplied; this is a numerical robustness
and efficiency task.

`input/` contains the complete operator, five public instances, the baseline
measurement, and `FORMAT.md`. `workspace/solve.py` is the starting submission;
`baseline/solve.py` is the frozen baseline. All paths here are relative to this
participant directory.
For the public-run example, set `OUTPUT_DIR` to the writable output directory
specified in your launch prompt.

Submit a directory containing `solve.py`, invoked as
`python solve.py --input FILE --output FILE`. Write finite float arrays `delta`
and `z` in one NPZ. Package all required code/assets in your output directory.
The detailed equations, dimensions, conventions, and accessible helper path are
in `input/FORMAT.md`.

Under the fixed budget, solve at least 18 of 20 hidden instances, at least 3 of
4 in every family, and improve worst-family success by at least 0.25 over the
measured baseline. No credit for the normal state, wrong relative band signs,
or inaccurate weak gaps.

Use single-process Python with NumPy/SciPy only: one thread, no subprocesses,
external executables, network, or private-file access. Each fresh invocation
receives 12 CPU seconds including startup, 2048 MiB address space, and an
1800-second wall safety ceiling. Wall time is not a performance score.
All submitted code/assets together must be at most 32 MiB.

Score is the minimum family acceptance fraction. A case passes only if the
independently recomputed normalized gap residual is at most `2e-8`, the
renormalization residual at most `2e-9`, and maximum per-patch normalized
distance to the certified branch at most `0.002`, with correct low-frequency
relative signs. A global sign reversal is equivalent. Exact norms are in
`input/FORMAT.md`; every quality gate and the resource gate is mandatory.
