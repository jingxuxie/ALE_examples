# Adaptive Symmetry Diagnostic Fleet

Commission a fleet of driven quantum spin rings under uncertain persistent
hardware regimes. Improve the supplied feasible fleet planner: manufacture
shared sensor and feedback designs, and assign each ring an adaptive diagnostic
policy under path budgets and fleet-wide branch capacities.

`input/` contains the physics and file specification, exact regime-resolved
response catalogs, and three example fleets. `baseline/` is a runnable planner
and catalog reader. `workspace/` is available for development.

Submit a self-contained directory containing `solve.py` and any dependencies:

```
python3 solve.py --input INPUT_DIRECTORY --output OUTPUT_JSON
```

The output is one fleet policy in the documented schema. Minimize the largest
scenario expected quantum loss across all rings in that fleet. The evaluator
recomputes losses from spin dynamics and checks every manufacturing, capacity,
and realized-path budget constraint. Reported losses are neither needed nor
accepted.

Hidden fleets cover drifting regime priors, sector-capacity congestion, and
frustrated dynamics with symmetry-breaking bridge kicks. Passing requires at
least **2.5% mean relative minimax-loss reduction** against the frozen baseline
and **1% reduction in the worst family**. Families have equal weight. Invalid
policies fail; no particular policy or global optimum is required.

Each fleet runs in a fresh process with **60 seconds, one logical CPU, and
2 GiB address space**. CPython `/usr/bin/python3`, NumPy 1.21.5, and SciPy 1.8.0
are available. No network or external executables/dependencies are provided
beyond the system Python environment. Input and submission files are read-only;
use `/tmp` or the output directory for temporary files. The submission limit is
128 MiB, 4096 regular files, and no symlinks. Hidden data and evaluator code are
not available during development or inside the solver runtime.
