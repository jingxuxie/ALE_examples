# Prior local package review

Inspected the existing `tasks/probing_quantum_processor_performance_with_pygsti__2002_12476`
participant specification, private solver, and status. Its task was **Drift-Aware
Gate-Set Triage**: update a finite, explicitly supplied hypothesis/regime mixture
from rastered counts, compute value of a one-shot diagnostic, and solve a
multiple-choice budget allocation. The public specification supplied complete
Bayes update and expected-utility rules. The private implementation used
matrix propagation, normalized likelihoods, and a budget dynamic program.

The recorded private reference score was 100 and passed. The only recorded
fresh trial used gpt-5.6-sol with 600 seconds and timed out; status reports a
calibration-circuit wrapper failure and zero score. This is not a successful
fresh-agent champion and is not evidence for the present one-hour model.

We did not reuse that task, its data, or its reference implementation: the
generalized solver largely reduces to standard filtering and knapsack once the
complete formulas are supplied. The present tasks instead require robust sparse
experimental design, physical adversarial construction, and learning unknown
history-dependent dynamics. None of the inspected private artifacts is in a
participant allowlist.
