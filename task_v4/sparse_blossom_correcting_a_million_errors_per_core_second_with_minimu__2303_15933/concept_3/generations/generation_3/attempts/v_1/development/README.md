# Development checks

Run these commands from the submission directory, setting `P` to the provided
read-only participant directory:

```sh
export P=/absolute/path/to/participant
export PYTHONPATH="$PWD:$PWD/development"
/usr/bin/python3 development/verify.py
/usr/bin/python3 development/experiment.py --episode 5 --seed 11 --random-rates --output development/recheck.json
/usr/bin/python3 development/summarize.py
```

The final public protocol reports are `final_report0.json` through
`final_report5.json`. Their `final_test*.log` files include `/usr/bin/time -v`
statistics from workers subject to 60 CPU-second and 3 GiB address-space
limits. `portable_test.log` additionally checks the non-AVX2 implementation.
The `finalrand_*.json` records contain 24 independently randomized-rate tests
with seeds 11 through 14 across all six public graph specifications. The
simulator and the revealed public rates are used only by these development
drivers, never by the submitted worker.

`archive/` preserves exploratory policies, transcripts, and comparison reports.
They are not runtime dependencies of the submission.
