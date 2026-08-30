# Private search provenance

This sidecar uses only the public frozen router, validator, and evaluator. It does
not read attempts or fresh-agent outputs, modify participant/evaluator source or
status, launch agents, or change targets. Artifacts remain under the authorized
private search names and candidate directory; the optional private result JSON is
also mirrored to `evaluator/hidden/private_search_result.json`.

## Method

The genome is a physical schedule of adjacent gates and SWAPs. Tracking occupants
from identity yields logical circuit demands and an explicit route. All candidate
trials pass the actual demand and replay validator before scoring. Local mutations
change edge choices, gate order, SWAP location, and schedule length. Twelve seeded
islands explore the three supplied hardware graphs with simulated-annealing
acceptance and elite retention. An optimistic early cutoff rejects candidates
already beaten by one portfolio member; promoted candidates run the entire
available portfolio under all six public relabelings.

`private_search_router.cpp` is a private acceleration of the supplied algorithm,
not a change to the method under test. Before search, it matched 324 independently
replayed trusted Python routes, across three graphs, two random circuits, three
labelings, and the 18 settings actually present at that point. No native proxy
score is treated as a final certificate. Saved champions are rerun through the
unaltered evaluator in isolated Python subprocesses.

## Reproduction

Compile `private_search_router.cpp` to `private_search_router.so` with
`g++ -O3 -std=c++17 -shared -fPIC -ffp-contract=off`.
From concept_2, run
`python -B adversary/private_search.py --seconds 900 --workers 12 --seed 28082026`.
`--parity-only` checks the acceleration and `--finalize-only` reruns exact checker
validation of saved island champions. Numbers tested are **candidate trials**,
not a claim of distinct circuits; mutations can revisit circuits.

## Scope of claims

The requested 36-setting portfolio does not match the source initially supplied:
`router.settings()` returned 18. The run records source hashes and the exact
configuration count returned by every final checker family. A pass under the
available exact checker must not be represented as verification of an unspecified
36-setting version. The final JSON makes this distinction explicit.

An early exact-validated ladder16 witness is preserved in
`private_candidates/checkpoint_champion/`. Its reference uses nine SWAPs for
109 gates; the six winning portfolio routes use 56 through 59 SWAPs. All winners
have zero fallback SWAPs. All 32 additional, unoptimized random relabelings also
meet the fixed numeric targets. These are diagnostic checks, not new grading
families. Coverage and reference-SWAP placement are recorded in its diagnostics.

The evidence supports genuine distance-heuristic routing overhead, rather than
invalid routing, idle-wire padding, a single physical-label tie, or forced
shortest-path fallback. It does not prove the reference is optimal, establish a
general approximation lower bound, or refute a theorem in either cited paper.
The final `private_search_result.json` and candidate exact reports are authoritative
for the strongest saved result and the actual configuration count at completion.
