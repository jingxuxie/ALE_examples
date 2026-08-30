# Robust band atlas solver

Run:

```sh
python3 solve.py --input CASE_DIRECTORY --output OUTPUT_JSON
```

The submission consists of `solve.py`, `bounds.py`, `optimizer.cpp`, and
`optimizer.so`. The compiled optimizer is included; if it is absent, the Python
entry point builds it with a C++17 compiler. NumPy, SciPy, and the supplied
`atlas` utility are the only Python dependencies.

The solver starts from the frozen feasible baseline. A scenario-aware linear
relaxation includes the acquisition budget, anchors, edge/face marginal
consistency, and determinant-bundle Chern constraints. Its reduced costs guide
domain pruning and branch-and-bound. A timed, four-worker annealing fallback
uses single-site, budget-exchange, and block moves. The final choices are checked
with the supplied evaluator and replaced by the baseline if infeasible or worse.
The internal wall-time budget is 78 seconds, leaving startup and output headroom.

## Public validation

| Family | Baseline objective | Submitted objective | Reduction |
| --- | ---: | ---: | ---: |
| Anisotropic warping | 0.686524402 | 0.646903484 | 5.7712% |
| Gap hotspots | 0.728024073 | 0.676824830 | 7.0326% |
| Inversion proximity | 0.722860599 | 0.617780255 | 14.5367% |
| Scenario competition | 0.769078349 | 0.743190416 | 3.3661% |

All four public outputs are feasible and improve on the baseline. The
family-balanced public reduction is **7.6767%**. The LP-guided search closes on
all four cases. The public scenario-competition case alone is below the 5.7%
family threshold; even its LP lower bound of 0.740124418 precludes a 5.7% case
reduction. No hidden-family acceptance result is claimed.

Additional checks use transformations of the supplied assets: independently
permuted candidates, nonsingular local frame changes, reordered scenarios,
momentum reflection with reversed Chern number, a 9-by-8 grid, and a zero-Chern
constraint. All produce feasible, non-regressing outputs under a 2 GiB address
space limit. Test scripts and generated scratch data are not solver inputs.
