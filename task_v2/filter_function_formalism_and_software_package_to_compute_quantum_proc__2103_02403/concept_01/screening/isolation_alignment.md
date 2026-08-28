# Replay isolation alignment

Before any participant output was graded, the replay namespace was aligned
with the public access contract. The task permits the current participant
directory and the attempt directory. Both remain readable at their original
absolute paths during evaluation, as well as the evaluator's `/candidate`
alias. This avoids turning a legitimate reference to supplied dependencies
or the attempt's own workspace into an undocumented relocation failure.
The candidate and participant trees are read-only during replay. Only the
new case and run-output directory are added; labels, reference solvers,
other attempts, source paper and network remain inaccessible.

No task inputs, hidden cases, targets, numerical tolerances, scoring formulas,
time limit, model configuration or scientific requirements changed. The
participant has received no feedback or additional instructions.
