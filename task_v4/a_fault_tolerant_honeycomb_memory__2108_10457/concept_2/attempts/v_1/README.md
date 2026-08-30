# Honeycomb heralded-phase-erasure design

The submission is `design.json`, a 62-byte regular JSON file. No program needs
to be executed. It uses the supplied 24-site ordering and repeats unchanged
on all three lattice sizes.

For each listed horizontal coordinate, the six entries run from y=0 to y=5:

| x | Original-frame images of laboratory Z |
|---|---------------------------------------|
| 1 | Y X X Z Z Y |
| 3 | Z Z Y Y X X |
| 5 | Y X X Z Z Y |
| 7 | Z Z Y Y X X |

## Validation

All reported scores use the supplied exact checker, including all four
logical Pauli coordinates. The design was fixed before the final holdout.

| Supports | Core score | Worst group | Mean ambiguity |
|----------|------------|-------------|----------------|
| Supplied practice, 48 per group | 0.993056 | 0.937500 | 0.009259 |
| Fresh seed 731, 2,048 per group | 0.993218 | 0.950195 | 0.007053 |
| Final seed 142857, 10,000 per group | 0.993000 | 0.947500 | 0.007511 |

The final holdout contains 90,000 independently generated supports. Its
group correctability fractions are:

| Qubits | Independent | Spatial stripe | Temporal burst |
|--------|-------------|----------------|----------------|
| 24 | 0.9898 | 1.0000 | 0.9475 |
| 96 | 1.0000 | 1.0000 | 0.9998 |
| 216 | 1.0000 | 1.0000 | 0.9999 |

These empirical results exceed the 0.85 core target and every 0.60 group
floor with substantial margins. They are not a claim about ordinary noise,
unheralded decoding, or a guarantee for particular hidden supports.

From the participant directory, reproduce the final check with:

```
python workspace/check_design.py ../attempts/v_1/design.json --seed 142857 --count 10000
```

The accompanying JSON score reports retain the complete official-checker
outputs. Development sources record an exact GF(2) simulated-annealing search,
enumeration of all 116 perfect matchings of the supplied 24-site graph, and
testing of 2,306 variants within two site edits of the two leading structured
patterns. The optimized scorer was cross-checked against the supplied Python
checker. No external data or hidden supports were used.
