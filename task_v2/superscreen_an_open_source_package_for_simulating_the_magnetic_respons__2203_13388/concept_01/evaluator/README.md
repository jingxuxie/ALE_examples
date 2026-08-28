# Private pilot evaluator

Run with the trusted dependency and helper snapshots, not participant-modified
Python code:

```
PYTHONPATH=SOURCE/runtime:EVALUATOR/support OPENBLAS_NUM_THREADS=1 \
  python EVALUATOR/evaluate.py --submission OUTPUT --output RESULT.json
```

The executable is rerun inside a network-disabled bubblewrap namespace. Only
the current participant tree, the submitted output, system runtime, and a
staged copy of one input device are mounted. Oracle arrays are never mounted.
The grader uses its private helper and public-input snapshots. Numerical
oracles use order-10 target quadrature; the order-6 reference is independently
checked against these and against adaptive integration of individual triangles.

Component error scores are 1/(1+(relative_error/0.08)^1.3), with an additional
95th-percentile local error term for spatial current and field. Components
cover streams, currents, vector fields, hole states, fluxoids and inductance.
Consistency checks tie currents to streams, hole values to topology, and
fluxoids to the conservative reaction of the submitted state. The core score
is 0.7 times the mean family score plus 0.3 times its minimum. Overall score is
0.85 core + 0.10 measured resource score + 0.05 reproducible evidence score.
Thus clerical failure alone cannot establish frontier hardness.

Families are not seed variations: annular kinetic response, asymmetric
three-hole coupling, an official five-film IBM layout, a close three-sheet
screening stack, a discontinuous material island, and a vortex-bearing slit
with no topological hole. Different source/control conditions coexist.

The source-integral shortcut alone leaves material assembly, global response,
vortex source deposition and fluxoid control unresolved. A generic linear solve
alone does not construct these operators. The underlying linearity is physical,
not a shared synthetic label generator that reveals the answers.
