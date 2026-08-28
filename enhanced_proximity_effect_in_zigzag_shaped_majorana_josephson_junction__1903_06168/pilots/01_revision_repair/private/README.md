# 01 — Historical revision repair (A/F)

This is **one pilot concept**, not four tasks and not a production acceptance.
No fresh agents were launched by this builder. The runnable reference and baseline
both complete all 12 requests. Stored end-to-end reports are in `reference/`.

## Source-grounded scope

The participant gets the byte-exact `zigzag.py` from
`a04132fedb8cbd5cf7a1365428015cefab047538`, the parent of `7bc79e9`.
The private reference gets the byte-exact file from
`ff2b0e0ee07aa1d28634db192c8ef384a0496e8b`. The source repository is
basnijholt/zigzag-majoranas; full identifiers and SHA-256 values are recorded in
`reference/SOURCE_MANIFEST.json`. The upstream license and attribution are retained
in both snapshots' directories; the license was copied from the later revision,
since the starting revision did not contain `LICENSE.txt`.

All four requested commits were inspected:

| Commit | Actual change relevant to this pilot | Treatment |
| --- | --- | --- |
| `7bc79e9` | Replaces the active two-axis slicing implementation with a generalized implementation using early-bound lambda defaults. | The parent's active two-axis code already works; the problematic generalized code is commented out there. No invented active late-binding defect or scalar-indexing exception is scored. |
| `06acb1b` | Changes the outer-edge condition from `self.shape(site)` to `not self.shape(site)`. | Selected: changes the composed barrier predicate and, through fill order, the Hamiltonian. This intermediate commit also has a misplaced docstring; the later reference is syntactically valid. |
| `00b1c82` | Selects the objective value from `scipy.optimize.brute(..., full_output=True)` instead of returning the minimizing coordinate. | Selected: gap values must be energies, including off-grid minima. |
| `ff2b0e0` | Replaces undefined `template_sc_top/bot` names with dictionary lookups when attaching superconducting leads. | Inspected, but no `sc_leads=True` cases. A NameError is not a substantive bottleneck or an intended source of low scores. |

The adapter supplies Kwant/SymPy function-printer compatibility, the grid keyword
adaptation, unused argument compatibility, and a deterministic SciPy sparse
eigensolver in place of MUMPS. These are public setup, not scored repairs.
No installed runtime, source checkout, or network access is needed by a submission:
Kwant/tinyarray are vendored with metadata, including their licenses.

## Core outcomes and anti-compression audit

The original source is one file. `geometry.py`, `hamiltonian.py`, and `protocol.py`
are explicitly author-added service layers, not evidence of separate upstream
files having independent bugs. Two real components interact: shape composition
determines which lattice sites receive the barrier, and those onsite terms alter
the band Hamiltonian whose minimum energy is returned by the gap estimator.

There are genuine case differences: straight versus stepped boundaries, one versus
two zigzag periods, lattice rescaling, asymmetric superconducting widths and
couplings, transverse spin-orbit toggling, chemical-potential convention toggling,
and near-band-bottom versus dispersive interior minima. The current spectral pool
has **only interior minima**; it does not establish endpoint coverage.

The monitoring families are `boundary_finite` (3), `boundary_wrapped` (3), and
`gap_interior` (6). Two finite/wrapped pairs are deliberate equal-response controls:
wrapping alone does not change these onsite probes. Do not count them as independent
bottlenecks, or claim that three family labels imply three methods are necessary.

**Can one fixed general solver handle every case? Yes, after a small repair.**
Dense diagonalization alone is insufficient: it diagonalizes the wrong matrix
if the outer-edge predicate is wrong, and cannot fix an energy/argmin mix-up.
However, dense diagonalization plus the correct geometry and scalar reduction is
entirely viable at these sizes. There is no claimed scale barrier. A compact repair
of the two selected functions can solve this pilot; `reference/validate.py` measures
geometry-only, gap-only, and combined repairs. This is an honest small repair probe,
likely rejectable if a fresh attempt solves it, not a demonstrated hard task.

## Evaluation

Only `response` arrays or scalar `gap` values are scored. Requests are staged under
neutral temporary filenames and passed through the documented CLI. References are
precomputed; evaluation imports no numerical model or reference solution. For each
case, let `error` be core-output RMSE and `weak_error` the unrepaired baseline's
RMSE against the stored reference:

`score = 1 / (1 + 99 * (error / weak_error)^2)`.

This is continuous, with reference 1 and the calibrated weak baseline 0.01, without
an arbitrary all-or-nothing numerical tolerance. The mean gives each family equal
weight; the worst family and per-case errors are retained. Missing, malformed,
nonfinite, crashed, and timed-out results score zero with distinct diagnostics.
Those failures must not be presented as evidence of scientific difficulty.
Runtime is measured but is not part of the core score.

Limits: 60 seconds, 2 GiB address space per subprocess, 2 MiB result JSON. Single
BLAS threads are configured. The actual stored spectral matrices have 416–640
orbitals; the largest barrier case has 1,408. These are bounded integration tests,
not realistic-scale spectral performance claims. The public ceiling is 2,400
orbitals. Native runtime: CPython 3.10, Linux x86_64; system NumPy/SciPy/SymPy are
required. Adaptive, pfapack, MUMPS, external leads, and rough boundaries are unused.

The evaluator is an execution harness, **not a filesystem security boundary**.
An orchestrator launching participants must isolate `participant/` and `attempt/`
from `private/` and the original source repository. Runtime files are already
inside `participant/`, so no private read allowance is necessary. Keep the initial
`attempt/` empty; author checks use temporary private directories instead.

## Exact commands

From the pilot directory:

```sh
PYTHONDONTWRITEBYTECODE=1 python private/evaluator.py --submission private/reference/solve.py --report private/reference/reference_report.json
PYTHONDONTWRITEBYTECODE=1 python private/evaluator.py --submission participant/workspace/solve.py --report private/reference/baseline_report.json
PYTHONDONTWRITEBYTECODE=1 python private/reference/validate.py --source-repo ../../source/zigzag-majoranas --write
PYTHONDONTWRITEBYTECODE=1 python private/evaluator.py --submission attempt/solve.py --report private/attempt_report.json
```

To regenerate requests, strong outputs, weak calibrations, and metadata:

```sh
PYTHONDONTWRITEBYTECODE=1 python private/reference/precompute.py --write
```

Author-created persistent files and reports are written through `apply_patch`.
Executable submissions naturally write their requested result files; transient
runtime extraction and subprocess staging are cleaned up. `validate.py` checks
source-byte provenance, license preservation, syntax, direct analytic geometry
against assembled barrier responses, Hermiticity, dense/sparse spectral agreement,
stored gap refinements, normalization, invalid-result handling, repair ablations,
and the initially empty attempt directory. The independent gap search uses a
65-point grid with bounded local refinement; dense eigenspectra check its resulting
minima. This is numerical validation, not a proof of the global minimum for arbitrary
requests outside the bounded pool.
