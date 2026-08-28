# Confirmation decision protocol

Recorded while the activation ratchet-1 fresh attempt is running, before its
submission or evaluation is inspected. Case/reference/scorer hashes were frozen
before model launch at 2026-08-28 03:06:03 UTC. No further thermal ratchet is
eligible: its original pool and the validated physical counterexample are solved.

For activation, retain every one of the eleven frozen cases: six initial and
five independently parameterized held-out cases. There are four boundary,
four soft-interface and three coherent cases. Do not select a subset after
observing the model's performance. Compute each family's mean over all its
cases, then report the mean of those three family means and their minimum.
Also retain both original per-split reports, individual failures, runtimes and
memory. The 0.7-mean + 0.3-worst aggregate reported by the evaluator is supplementary;
it is not substituted for the core mean to make acceptance easier.

Acceptance requires all of:

- Independent source certification remains valid and both strong replay splits
  exceed .90, including their worst families.
- The public mission and execution contract are complete; all protected hashes
  still match, and the model had only its allowlisted participant/attempt.
- The new model's combined family-mean core score is below .70.
- At least one central component has substantive scientific/algorithmic or
  resource-scaling failures. Schema, dependency, permission, sandbox or incidental
  startup failures alone do not establish difficulty.
- A low score is not caused by the participant discovering a genuinely better
  physical saddle than the reference. Any such discrepancy must be investigated
  before deciding; native certification is not an exhaustive optimality proof.

A combined core score at least .90 is solved under the screening rule. For
.70–.90, consider at most one additional source-grounded ratchet only if a genuine
failure region and a valid reference exist. Worst-family and individual-case
performance inform that decision; do not hide a central failure by averaging.
Do not add random cases, change physical tolerances, or introduce a fifth concept.

If no task survives, deliver an explicit rejection with the complete evidence.
If a task survives, the production evaluation uses all eleven cases rather than
only whichever split happened to be harder. No hidden answers or source-native
solution modules become participant artifacts. A copied production package must
be revalidated through its own paths before marking the objective complete.
