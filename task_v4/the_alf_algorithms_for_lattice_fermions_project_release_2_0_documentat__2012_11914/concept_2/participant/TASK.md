# Positive checkerboard propagator

**Mode C — WITNESS / DESIGN CONSTRUCTION.** Construct one universal positive
33-stage schedule for finite imaginary-time propagation, rooted in ALF 2.0
Sec. 2.3 symmetric checkerboard factorization. Jointly design the component
word and coefficients; checkerboard matchings are fixed. No higher-order proof
is required.

## Witness

Write **`OUTPUT/submission.json`** in your writable output directory;
`participant/` is read-only. JSON contains exactly `schema_version: 1` and
`stages`: exactly 33 objects with exactly `component` and `coefficient`.
Components are `X0,X1,Y0,Y1,V`; adjacent components differ. The word is
palindromic, reflected coefficients agree within `1e-12`, and each component's
coefficients sum to one within `1e-10`. Coefficients are finite numbers in
`[0.00001,1]`. After validation, reflected coefficients are averaged pairwise
for numerical evaluation; no other normalization occurs.

Strict JSON, no duplicate keys, maximum 32,768 bytes; submit a regular
nonsymlink file. No instance-dependent choices, negative times, new operators,
mixtures, or executable submissions.

## Domain and target

The product is `P(h)=exp(-h*a[0]*H[c[0]]) ... exp(-h*a[32]*H[c[32]])`.
The binding **`input/spec.json`** publishes every law, constraint and metric.
Eight families cover fluctuating and uniform onsite fields on periodic
`4x4,4x6,6x4` lattices, with `h=.4,.6,.8,1` and repetitions `1,4`.
There are 48 independent public training instances and 96 held-out instances.

Independent exponential/spectral checks measure propagator and Green-function
errors against equal-cost repeated Strang. Passing requires
**core_score >= 1.80**, **worst_family_score >= 1.35**, and
**maximum pointwise error ratio <= 1.00**. Baseline scores are 1.
Targets are fixed; no passing witness is promised.

```sh
python3 baseline/build.py --output OUTPUT/submission.json
```

Run from the provided participant directory. Python 3, NumPy and SciPy suffice.
Search budget: one hour, four CPU threads. Evaluator worker caps are separate
and published in the contract.
