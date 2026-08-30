# Shared nodes for uncertain damped-rational interpolation

Build a finite-degree optimizer that outputs **one shared node vector** for all
explicitly supplied prefactors on the half-line. Better interpolation conditioning
can reduce numerical error amplification in polynomial matrix computations.

For degree `d`, each input scenario is

    mu_s(x) = exp(-a_s*x) / product_p(x+p),  x >= 0, a_s>0, p>0.

Repeated poles represent multiplicities; an empty pole list is allowed. Return
`d+1` ordered, distinct, nonnegative nodes `t_i`. With

    ell_i(x) = product_{j != i} (x-t_j)/(t_i-t_j),
    Lambda(T) = max_s sup_{x>=0} sum_i |ell_i(x)|*mu_s(x)/mu_s(t_i),

minimize `Lambda(T)`. This is the actual finite-degree worst-prefactor supremum,
not an average error, a limiting density, or a nominal-prefactor objective.
Prefactor multiplicative constants have no effect. No functions or optimal nodes
are hidden inside an input: all scenarios to be controlled are explicitly given.

## Assets and interface

`input/schema.json` specifies inputs; four small JSON examples cover damping
uncertainty, near-origin repeated poles, separated pole clusters, and uncertain
pole models/counts. Hidden cases vary degrees and cluster scales. The supported
degree range is 2–48 with 2–6 scenarios and at most 24 poles per scenario.
`baseline/solution.py` is the canonical self-contained starting implementation;
`workspace/baseline/solution.py` is an identical convenience copy.

Submit a self-contained directory with `solution.py`; run as

    python solution.py INPUT.json OUTPUT.json

from **any working directory**. Write exactly `{"nodes": [number, ...]}` to the
output path (strict JSON; no NaN, infinity, booleans, extra keys, or duplicate keys).
Do not require files beyond the submitted directory and input. The evaluator does
not trust claimed scores, peak locations, certificates, or timing information.

For representability, set `y_i=min_s(a_s)*t_i`. Require
`y_d <= 10000*(d+1)` and every adjacent gap greater than
`64*2^-52*max(1,y_i)` (where i is the larger index).

## Objective and resources

Each case score is the frozen baseline's weighted supremum lower bound divided
by your weighted supremum upper bound. Family scores are geometric means of case
scores; core score is the equally weighted geometric mean of the four families.
The worst-family score prevents sacrificing a difficult family. Fixed thresholds
are recorded in `TARGET.json`; all thresholds and all validity checks must pass.

Development allowance: one hour for the fresh attempt. Execution budget:
8 CPU seconds per case, one process/thread, 1 GiB address space, 64 KiB
output. NumPy, SciPy, mpmath, and the standard library are available. Network and
private evaluator files are inaccessible. A 180-second wall watchdog accommodates
shared-host contention; CPU, not wall time, determines the resource score:
`max(0, 1-total_submission_CPU/(8*number_of_cases))`.

Scoring numerically encloses the half-line supremum to relative width 8e-5,
checks peaks at high precision, and accounts analytically for the infinite tail.
The enclosure itself is limited to 8 evaluator CPU seconds and 50,000 interval
subdivisions per case. Numerically unresolved, overflowing, or nearly coincident
configurations fail with an explicit reason rather than receiving a grid score.
These numerical checks are not formal interval-arithmetic certificates.
