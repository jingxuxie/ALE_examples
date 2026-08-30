# Six shapes, two different jet resolutions

## Mission
Construct **two physical massless five-parton CM events** with the same six
classical event shapes but a factor **at least 3** difference in Durham y45.
This is a nonlinear inverse phase-space search, not a formula-implementation task.
The counterexample challenges sufficiency of these six scalars as event-state
information, not EERAD3's accuracy or any claim that its authors made.

## Assets
`input/schema.md` is the full public contract; `input/contract.json` contains its
constants. `workspace/shapes.py` supplies reusable NumPy calculations and a CM
sampler. `baseline/search.py` is a deliberately weak random/multistart search.

## Interface
Write a UTF-8 JSON witness containing exactly `{"events": [event_A, event_B]}`.
Each event has five rows `[E, px, py, pz]`, in units of total CM energy Q=1.
From the participant directory, run
`python3 baseline/search.py --output OUTPUT_DIRECTORY/submission.json` as a starter.
The evaluator reads only this data file; claimed observables or code are not accepted.

## Condition
Match `(tau, C, rho_H, B_T, B_W, y23)` to absolute error <=1e-7 in each component;
require `max(y45_A,y45_B)/min(y45_A,y45_B) >= 3`. Both events must satisfy all
published physical and regularity cuts, with at least two partons in each thrust
hemisphere. The independent verifier also tests
permutation and rotation invariance. A copied, rotated or relabelled event fails
the separation condition. No written report or reference solution is required.

## Resources
Python 3 and NumPy; SciPy is permitted but not required. One CPU, 2 GiB memory,
one-hour authoring/search budget, no network or GPU. Only `TASK.md`, `input/`,
`workspace/` and `baseline/` are public assets. Submission data is at most 16 KiB.
