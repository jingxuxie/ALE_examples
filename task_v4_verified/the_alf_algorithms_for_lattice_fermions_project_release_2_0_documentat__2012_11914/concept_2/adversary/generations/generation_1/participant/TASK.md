# Positive checkerboard propagator

**Mode C — WITNESS / DESIGN CONSTRUCTION.** Design one universal positive
splitting schedule, rooted in ALF 2.0 Sec. 2.3 symmetric checkerboard Trotter
factorization. Optimize a discrete component word and continuous coefficients;
the checkerboard matchings are already fixed. No higher-order proof is required.

## Witness

Write **`OUTPUT/submission.json`** in your writable output directory; `participant/`
is read-only. The JSON has exactly `schema_version: 1` and `stages`: exactly
33 objects, each containing exactly `component` and `coefficient`.

Components are `X0,X1,Y0,Y1,V`. Consecutive components differ. The word is
palindromic, reflected coefficients agree within `1e-12`, and each component's
coefficients sum to one within `1e-10`. Coefficients are finite numbers in
`[0.00001,1]`. Strict JSON, no duplicate keys, maximum 32,768 bytes; submit a
regular nonsymlink file. No instance-dependent choices, negative stages,
commutators, mixtures, or executable submissions.

The product is `P(h)=exp(-h*a[0]*H[c[0]]) ... exp(-h*a[32]*H[c[32]])`.
The complete binding contract, including every family law, tolerance, and
resource cap, is **`input/spec.json`**; see `input/FAMILIES.md` and the 24 public
training instances. Hidden samples follow those same laws.

## Target

Independent matrix-exponential checks compare propagator and Green-function
errors against an equal-cost, 33-stage repeated-Strang baseline over four
physical families, four finite steps, and two repetition counts.
Scores are inverse RMS relative-error ratios per family. Passing requires
geometric-mean **core_score >= 1.50**, **worst_family_score >= 1.20**, and
**maximum pointwise error ratio <= 1.15**. Baseline scores are 1. Targets are
frozen; no passing witness is promised.

```sh
python3 baseline/build.py --output OUTPUT/submission.json
```

Run from the provided participant directory. The evaluator remains harness-side.
Python 3, NumPy, and SciPy suffice. The search budget is one hour and four CPU
threads; independent scoring uses the worker limits in the contract.
