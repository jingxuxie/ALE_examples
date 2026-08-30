# Hardware-local Slater preparation

Prepare each supplied occupied projector from its specified occupation bitstring
using particle-number-preserving two-mode gates on the supplied hardware graph.
Both the gate count and the parallel depth must fit the instance's hard budgets.
The four instances have 14–18 modes and 7–9 particles on two hardware families.

## Assets and interface

- `input/instances.json`: targets, hardware edges, initial occupations, tolerances,
  and resource budgets. All scored instances are supplied.
- `input/format.md`: exact gate convention, JSON schema, and mathematical checks.
- `workspace/simulator.py`: public simulator and development scorer.
- `baseline/compile.py`: runnable, exact general-purpose compiler with routing;
  its output is not expected to satisfy the resource budgets.

Submit a directory containing **`solution.json`**, with one layered circuit for
each instance. The evaluator reads this artifact; it does not execute your code.
No ancillas, additional phases, relabelings, measurements, or unlisted gates are
free. The hardware edges describe native **fermionic mode** operations, not a
particular qubit encoding.

The participant task tree is **read-only**. Use the writable output path supplied
in your launch prompt, represented here by `$OUTPUT_DIR`. From this directory:

```bash
python3 baseline/compile.py --output-dir "$OUTPUT_DIR/baseline_output"
python3 workspace/simulator.py "$OUTPUT_DIR/baseline_output" --report "$OUTPUT_DIR/report.json"
```

Python 3 and NumPy suffice for these tools; SciPy is available in the build
environment. The development time limit is **one hour**. There is no separate
participant-runtime score; synthesis within that limit is your choice.
The artifact is limited to 2 MiB; larger emergency parsing limits are
specified in the format document, not substituted for the hard circuit budgets.

The main score is the fraction of instances certified accurate **and** within
both budgets. The worst-family score prevents success on only one hardware
family. A secondary resource score measures resource compliance of accurate
circuits. Full success requires every instance to pass. Numerical accuracy alone
does not earn main-score credit for an over-budget circuit.
