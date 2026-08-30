# Private exact generation-2 refinement

This directory alone is writable for this experiment. It is not participant
material. The initialization is the private generation-1 champion; all frozen
generation-2 hidden matrices are used with explicit privilege. The artifact is
one static universal 33-stage schedule, never an instance-dependent program.

`refine.py` computes exact finite-step pointwise error Jacobians for the fixed
component word. It uses a multiplicity-weighted component softmax with positive
floors, reverse differentiation of the positive half product, and spectral
divided differences for both observables. Central finite differences must pass
before optimization starts. L-BFGS powers 8, 16 and 32 are followed by an
analytic-Jacobian SLSQP minimax phase if necessary. Optimization CPU and wall
time are each capped below 600 seconds; setup, gradient checking, and final
official validation are reported separately. No passing result is assumed.

Run from the concept root:

```sh
python3 -B adversary/exact_refine/refine.py --seconds 600
```

All outputs, initialization copies, verification logs and reports remain here.
Protected participant/evaluator hashes are checked before and after. A model
pass is not a validated pass until `official_report.json` says so.

`order_refine.py` optionally consumes only the remainder of the same shared
600-second optimization budget. It first minimizes a common epigraph for all
normalized point, family, and core gates on the fixed word, then checks a small
word neighborhood with the same exact coefficient gradients. Its witness and
official result are `refined_submission.json` and `refined_official_report.json`.
The first phase's CPU use is subtracted and a further ten-second reserve is
kept. It never resets the optimization budget.
