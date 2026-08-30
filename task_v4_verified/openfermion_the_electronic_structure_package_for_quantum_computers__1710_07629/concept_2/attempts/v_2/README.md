# Hardware-local Slater preparation submission

`solution.json` is the artifact consumed by the evaluator. It contains one native,
layered, particle-number-preserving circuit for each supplied instance.

`report.json` records the public simulator's accuracy and resource checks.
`isolation_audit.json` records the required initial access check.

From this output directory, reproduce validation with:

```bash
python3 ../../participant/workspace/simulator.py . --report report.json
```

The synthesis experiments use analytic occupied-frame derivatives, sparse
nonlinear fitting, gate-placement searches, exact phase-aware gate merging,
and disjoint-edge scheduling. `assemble.py` selects the best accurately verified
candidate for each instance, preferring certified circuits. Other Python files
and logs retain the development experiments; the evaluator needs only
`solution.json`.
