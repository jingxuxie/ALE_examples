# Handoff observations

The historical impurity model uses a spin-adapted integral interface. The
current integration layer was later changed to spin-resolved states. The group
ported the same coefficient preparation and added JSON graph input, then
started using it for more general contacts. A smooth trace was treated as a
successful run.

Observed problems, not established causes:

- Increasing sweep count sometimes changes very little while changing the
  physical representation changes the apparent transport signal.
- Runs with magnetic phases have unusually similar traces to real-hopping runs.
- A regional charge check is harder to interpret in paired contacts.
- Low-bond calculations can have nearly conserved norm and energy but disagree
  on the current. It is unclear whether the state preparation or propagation
  dominates that discrepancy.
- Adding an oscillator did not obviously change the old summary plots.

We need a scientifically interpretable result, not just suppressed warnings or
a larger default bond dimension. Preserve the input meaning, investigate the
failures, and document the limits of the evidence.
