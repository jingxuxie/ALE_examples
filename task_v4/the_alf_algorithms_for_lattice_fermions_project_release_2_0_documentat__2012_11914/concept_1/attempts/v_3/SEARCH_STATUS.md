# Search unsuccessful

`witness.json` contains the best candidate selected by the search, but it is
**not a passing counterexample**. Both flavor determinants are positive at all
three required certification points. Independent calculations at 65 and 95
decimal digits agree to substantially better than the required tolerance.

`verification.json` records those results and explicitly sets `passes` to false.
Run `python verify.py` to reproduce the checks; it exits with status 1 for this
non-passing candidate.

The search scripts and logs are retained for reproducibility. No legal
negative-weight witness was found within the search budget. This unsuccessful
search is not a proof that the screening claim is true.
