# Hardware-local Slater preparation submission

`solution.json` is the submission artifact. It contains one hardware-local,
particle-number-preserving layered circuit for every supplied instance.

`report.json` records validation by the supplied public simulator, including
accuracy, gate count, depth, and certification for each instance. `selected.json`
identifies the source candidate selected for each circuit. The report is the
authoritative statement of which hard budgets are satisfied; an accurate circuit
is not necessarily resource-certified.

`isolation_audit.json` records the required initial access check. The remaining
Python files and logs support the numerical and exact circuit-synthesis searches.
All development outputs are contained in this directory.

To revalidate from the supplied participant directory:

```bash
python3 workspace/simulator.py /path/to/this/submission --report /path/to/this/submission/report.json
```
