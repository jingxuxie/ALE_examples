# Private counterexample search result

**A valid passing witness exists for the supplied exact checker.** Important scope
qualification: the frozen source exposes **18 configurations**, not the requested
36. All 18 configurations in every official family were rerun and independently
replayed. No pass against an unspecified 36-setting version is claimed. Both
source-path aliases refer to the same file, and all four trusted source hashes
remained unchanged throughout this sidecar run.

## Final certificate

- Artifact: `private_candidates/best/witness.json`.
- SHA-256: `07b8026e322e4c54e7d2e33b98413df437d5c2c5cbe31f8a638cf351b8c3fc20`.
- Hardware: grid16; 94 demands; explicit reference route: 8 SWAPs, 118 native 2q operations.
- Exact result: valid=true, passed=true, core_score=1, worst_family_score=1, resource_score=1.
- Fixed targets remain 2.5x SWAP count, 1.35x total native count, and 16 additional SWAPs.

| Relabeling | Best portfolio SWAPs | SWAP ratio | Native ratio | SWAP gap |
| --- | ---: | ---: | ---: | ---: |
| identity | 69 | 8.625 | 2.5508474576271185 | 61 |
| physical-11 | 68 | 8.5 | 2.5254237288135593 | 60 |
| physical-29 | 66 | 8.25 | 2.4745762711864407 | 58 |
| logical-47 | 69 | 8.625 | 2.5508474576271185 | 61 |
| joint-71 | 66 | 8.25 | 2.4745762711864407 | 58 |
| joint-103 | 66 | 8.25 | 2.4745762711864407 | 58 |

The per-setting counts and winning settings are in
`private_candidates/best/exact_result.json`. The reference certificate was checked
from the fixed identity placement, including every per-wire dependency, every
physical gate and SWAP adjacency, gate identity/orientation, and final placement.

## Search accounting

Twelve seeded islands each ran for 900 seconds. There were 2,037,027 generated
candidate trials, 1,995,576 valid trials, and 333,867 full accelerated portfolio
evaluations; the remainder of valid trials were screened by a failing portfolio
member. These are trial counts, **not unique-circuit counts**. The private C++
acceleration first matched 324 independently replayed Python routing runs.

Finalization exactly evaluated all twelve island champions, replaying 1,296
trusted portfolio routes in total. The final artifact was selected using exact,
uncapped target margins, not a reported proxy score. Full counters, source hashes,
candidate locations, actual setting count, and all exact results are in
`private_search_result.json`, mirrored to
`../evaluator/hidden/private_search_result.json` from the concept root's perspective
as `evaluator/hidden/private_search_result.json`.

## Mechanism and robustness evidence

All six official winning portfolio routes use **zero fallback SWAPs**. Thus the
observed gap is ordinary heuristic routing overhead, not the progress safeguard.
Demand coverage and partner counts satisfy the supplied regularity constraints;
there is no idle-wire padding or fabricated cost. The explicit low-cost inverse
route establishes an upper bound, not an optimality claim.

An additional 32 random joint relabelings, not used by the evolutionary objective,
were tested with every supplied setting and all routes were replayed. All meet
the fixed numeric targets. Their worst SWAP ratio is 3.25 and worst native ratio
is 1.4576271186440677. These are diagnostics, not changes to the grading families.
See `private_candidates/best/diagnostics.json` for detailed coverage and routing
evidence. The earlier ladder16 certificate and its independent diagnostic reports
remain in `private_candidates/checkpoint_champion/`.

No participant/evaluator source, status, attempt, or fresh-agent output was
modified or inspected beyond the permitted frozen-source reads. No fresh agents
were launched. The only unresolved request is verification against a 36-setting
definition, which was not present in the supplied source.
