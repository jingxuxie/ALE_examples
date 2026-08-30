# Fleet policy solver

Run with the system Python:

```
python3 solve.py --input INPUT_DIRECTORY --output OUTPUT_JSON
```

Dependencies are NumPy and SciPy, as supplied by the task environment.
The solver reads the response catalogs directly and writes only the required
policy schema. It does not need the participant directory or network access.

The planner combines feasible baseline constructions, shared-design search,
scenario and capacity lower bounds, sparse policy-tree linear relaxations,
capacity-constrained assignment, and bounded integer search. Every accepted
policy has integral branches and checked fleet capacities. A feasible incumbent
is saved atomically before optimization and whenever it improves.

The default search deadline is 54 seconds, including imports and input loading.
Numerical libraries use one thread. Optional development flags are `--verbose`
and `--seconds SECONDS`.
