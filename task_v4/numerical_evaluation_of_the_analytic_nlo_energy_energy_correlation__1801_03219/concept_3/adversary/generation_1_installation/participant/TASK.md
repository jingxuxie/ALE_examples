# Exact inverse energy–energy correlation

Construct **one static energy-flow event**, not a program implementing an EEC
formula. The fixed target is `input/target.json`. Any witness is acceptable;
recovering a particular event is not required.

## Event and constraints

There are 1024 planar directions at angles `2*pi*direction/1024`. Specify
512 integers in cyclic order, `a[0],...,a[511]`, one per antipodal pair.
Exactly 416 entries are zero, 64 are one, and 32 are two. Thus `sum(a)=128`.
Every occupied pair slot must have an empty slot immediately before and after
it, **including across the 511/0 boundary**.

Direction `direction` has energy `a[direction % 512]/256` and massless
four-momentum `energy*(1,cos(angle),sin(angle),0)`. Zero entries mean no particle.
Antipodal equality guarantees total energy one and exactly zero total momentum.
Directions are prescribed symbolically; do not submit floating-point momenta.

Match **every** published integer, without tolerance:

```
cyclic_autocorrelation[lag] =
    sum(a[slot] * a[(slot + lag) % 512] for slot in range(512))
```

All 512 lags are checked, including zero and 256. The EEC uses ordered pairs,
including self-pairs, as in arXiv:1801.03219 equations (1)–(2). For the full
1024-direction event, the weight at directed separation `lag` is
`cyclic_autocorrelation[lag % 512]/32768`. For an angular histogram with bins
`angle=2*pi*bin/1024`, `bin=0,...,512`, the two endpoint weights are each
`cyclic_autocorrelation[0]/32768`; every interior weight is
`cyclic_autocorrelation[bin % 512]/16384`. These are masses, not densities;
they sum to one. The target is a synthetic event, not a continuum NLO spectrum.

## Submission and scoring

Write `design.json` in your submission directory with exactly these keys:

```
{"schema_version": 1, "a": [512 JSON integers]}
```

The bracketed text is schematic, not literal valid JSON. See
`input/design.schema.json` and the executable `check.py`. Integers must be
JSON integer tokens, not booleans or decimals. Duplicate or extra keys,
non-finite values, symlinks, nonregular files, and files over 16384 bytes fail.
No submitted code is ever run. Other submission files are ignored.

`valid` means the schema, counts, and cyclic spacing hold; `passed` additionally
requires exact equality at all 512 lags. `core_score` is one only on a pass,
otherwise zero. Four contiguous 128-lag families each score one only if all
their lags match; `worst_family_score` is their minimum. Error norms and matched
lags are diagnostics, not partial credit. Rotation, reflection, and any other
exactly matching feasible event are accepted.

`runtime_seconds` measures checking, **not synthesis**. `runtime_score` and
`resource_score` are one for a valid bounded static artifact and zero otherwise;
they never compensate for a failed core constraint. No solver-time claim is
inferred from JSON. The target is fixed before attempts.

## Local commands

From this participant directory (Python 3.10+, NumPy for the baseline only):

```
python3 baseline/generate.py --output workspace --seed 1701 --restarts 4 --steps 60000
python3 check.py workspace --report workspace/local_report.json
```

The baseline is a bounded, count/spacing-preserving annealed local search, not
a promised solution. Its precomputed `baseline/design.json` is a starting point.
The authoritative grader uses its own fixed target. A nonmatching artifact is
a failed witness even if its histogram looks visually close.
