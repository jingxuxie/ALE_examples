# Exact inverse energy–energy correlation: 8192 directions

Construct one static massless, momentum-balanced energy-flow event matching the
**complete fixed two-point EEC** in `input/target.json`. This is inverse design,
not implementation of a supplied EEC formula. The construction budget is **one hour**.

Specify `a[0],...,a[4095]`: exactly **3328 zeros, 512 ones, and 256 twos**.
The integer sum is 1024. Occupied pair slots cannot be adjacent, including
across the 4095/0 boundary. There are 8192 prescribed planar directions with
angles `2*pi*direction/8192`. Direction `direction` has energy
`a[direction % 4096]/2048` and momentum equal to its energy times its unit
direction. Antipodal equality gives total energy one and total momentum zero.

Match all **4096 integer lags exactly**, with no tolerance:

```
c[lag] = sum(a[slot] * a[(slot + lag) % 4096] for slot in range(4096))
```

The EEC includes ordered self-pairs. Full directed-separation masses are
`c[lag % 4096]/2097152`. Folding to angular bins `bin=0,...,4096` gives endpoint
masses `c[0]/2097152` and interior masses `c[bin % 4096]/1048576`; the masses
sum to one. This is a synthetic single event, not a continuum NLO prediction.

Submit a directory containing static `design.json` with exactly
`{"schema_version": 1, "a": [...]}` and 4096 JSON integer entries. Do not submit
momenta or executable code. The size limit is **131072 bytes**. Any feasible
exact match is accepted, including rotations, reflections, or homometric events.

`valid` means the format, counts, and cyclic spacing hold. `passed` and
`core_score=1` require every lag to match. All other core scores are zero;
four contiguous 1024-lag families determine the binary worst-family score.
See `SPEC.md` for exact parsing, scoring, and histogram conventions.

From this participant directory:

```
python3 baseline/generate.py --output workspace --seed 1701 --restarts 4 --steps 60000
python3 check.py workspace --report workspace/local_report.json
```

The supplied bounded local-search artifact is not a promised solution. The
checker needs only Python 3.10+; the generator also needs NumPy. Any construction
algorithm is allowed within the same one-hour budget. The target is fixed before
attempts, and the authoritative evaluator uses a separately frozen copy.

`baseline/phase_projection.py` also supplies the parameterized constructor that
solved a lower-resolution predecessor. Run it as
`python3 baseline/phase_projection.py /path/to/output --seconds 120`.
It is a baseline, not a prescribed method or a promised solution at this scale.
