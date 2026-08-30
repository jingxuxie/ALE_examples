# Branch-correct anisotropic Eliashberg solver

## Mission
Improve the supplied executable nonlinear imaginary-axis solver. Recover the
nonzero, low-frequency same-sign superconducting branch across multiband,
retarded-scale, nearly critical, weak-interband, and combined materials. Physics
operators are already supplied; this is a numerical robustness and efficiency task.

## Assets
`participant/input/` contains the complete operator, its derivative API, five
public instances, and `FORMAT.md`. `participant/workspace/solve.py` is the editable
starting submission. `participant/baseline/solve.py` is the frozen baseline.

## Interface
Submit a directory containing `solve.py`. It receives
`python solve.py --input FILE --output FILE` and writes finite float arrays
`delta` and `z` in a single NPZ. See `participant/input/FORMAT.md` for the exact
equations, dimensions, conventions, and accessible helper path.

## Objective
Under the fixed budget, correctly solve at least 18 of 20 hidden instances, at
least 3 of 4 in every family, and improve worst-family success by at least 0.25
over the measured frozen baseline. No credit for the trivial normal state,
wrong relative band signs, or inaccurate weak gaps.

## Resources
Pure single-process Python with NumPy/SciPy only; one thread; no subprocesses,
external executables, network, or private-file access. Each invocation receives
12 CPU seconds including Python startup, 2048 MiB address space, and a generous
1800-second wall safety ceiling. Wall time is not a performance score.
Each case starts fresh. All submitted code/assets together must be at most 32 MiB.

## Scoring
Score is the minimum of the five family acceptance fractions. A case passes only
if the independently recomputed normalized gap residual is at most `2e-8`, the
renormalization residual at most `2e-9`, and the maximum per-patch normalized
distance to the certified branch at most `0.002`, with correct low-frequency
relative signs. A global sign reversal is equivalent. The exact norms are in
`FORMAT.md`; all three quality gates and the resource gate are mandatory.
