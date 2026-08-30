# Submission validation

The final artifact is `../submission/policy.py`, with `sampler.so`, its C++
source, and a short README. It is self-contained apart from installed runtime
libraries and NumPy. The four submission files total 51,536 bytes.

## Public protocol suite

All 12 family/shape combinations at public seed 2026 completed validly.
Mean family score: **0.85641753**. Worst family score: **0.80670976**.
Every episode used 12,000 shots in 374 experiments. These exceed the public
accuracy requirements of 0.50 and 0.3902439024, respectively. See
`protocol_audit_report.json` and the final snapshot runner's `final_public.json`.
These are development results, not a certified hidden-suite pass.

## Independent-seed stress tests

The final mixed acquisition design was also tested on 24 episodes spanning
4x5 and 5x5 grids, all four families, and base seeds 89162, 104729, and 871231.
The pooled family scores for 5x5 were 0.89861 (local), 0.86917 (distant),
0.83985 (anticorrelated), and 0.85440 (drift). For 4x5 they were 0.90942,
0.92957, 0.87744, and 0.87213. Maximum measured episode CPU was 30.95 seconds.
Details are in `stress_large.log` and `stress_middle.log`.

## Additional checks

- Python syntax validation succeeded.
- C++ compilation with `-Wall -Wextra -Wpedantic` produced no warnings, and
  rebuilding produced a byte-identical native helper.
- An artificially advanced deadline exercised the early-finish safeguard:
  the episode completed with 7,584 shots and 96 valid predictions.
- Full bubblewrap startup failed before policy execution because the host
  sandbox denied its NETLINK_ROUTE operation. A filesystem-only diagnostic
  also failed during tmpfs setup. No isolated-run certification is claimed.

To repeat the supplied snapshot-based public run from the output directory:

```
TMPDIR="$PWD/work" OPENBLAS_NUM_THREADS=1 python -B \
  ../../participant/workspace/develop.py \
  --submission "$PWD/submission" --policy policy.py \
  --family all --shape all --seed 2026 \
  --report "$PWD/work/final_public.json"
```
