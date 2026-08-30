# Trusted artifact evaluation

Expose none of this directory to the participant. Run from any directory:

```
/usr/bin/python3 -B evaluator/evaluate.py witness.json --output result.json --summary-only
```

Only the JSON artifact is read. The private validator rejects duplicate keys,
invalid UTF-8, nonfinite values, booleans in numeric slots, bad incidence/rate
constraints, symlinks, nonregular files, and files larger than 16 KiB. The
independent schedule is hardcoded in `hidden/oracle.py` and
`hidden/inherited_oracle.py`; participant files cannot alter acceptance.

`hidden/full_state.cpp` implements nonnegative probability and min-plus dynamic
programming over the full syndrome-plus-logical state space. An invertible GF(2)
basis processes independent transitions first; it is not a frontier or reference
solution. The numerical kernel is unchanged from audited generation two.

Build the trusted binary, without fast-math:

```
g++ -std=c++17 -O3 -shared -fPIC evaluator/hidden/full_state.cpp -o evaluator/hidden/full_state.so
```

The finite schedule has 5,791 points and one native thread, with a nominal
900-second independent evaluation allowance and 1 GiB memory allowance. Host
scheduling contention must not turn an otherwise valid artifact into failure.
No internal watchdog or runtime-dependent score is used. CPU seconds, wall
seconds, and peak RSS accompany standardized validity, scientific scores,
and exact-versus-certificate failure clusters.
