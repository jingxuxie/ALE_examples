# Fleet planner

Run with the system Python, NumPy, and SciPy:

```
python3 solve.py --input INPUT_DIRECTORY --output OUTPUT_JSON
```

The planner screens shared manufacturing designs using scenario and capacity
lower bounds, constructs feasible fleet policies, and refines promising designs
with linear-programming relaxations, capacity-constrained assignments, and a
bounded integer search. It uses the supplied response catalogs directly.

The output contains only the required fleet-policy fields. No additional files,
network access, external executables, or writable input files are required.
