# Frame-covariance and precision ratchet

Generation 2 was genuinely solved: its fresh isolated submission achieved
log-RMSE 2.655e-13 at 0.939 CPU seconds on 200,000 events. The production budget
alone no longer distinguishes the challenge from a solved task.

Privileged search transformed 10,000 physical events into CM, axis-aligned,
moderately boosted, and strongly boosted frames. The champion retains tiny
CM errors but has log-RMSE 8.47 and 29.92 in the two boosted families. Its
photon contraction is CM-specific, and its use of rounded four-momenta loses
information that the authoritative scalar invariants retain. This is a
physical covariance and representation-conditioning failure, not a label or
identity lookup exception.

Generation 3 fixes the 20 phase/frame intersections before launching a fresh
agent. Transformations agree with independent 100-digit boosts to 1.1e-16
relative vector error. Labels are the same quadruple-precision evaluations
of the invariant inputs, unaffected by frame choice. The mission now requires
cancellation-sensitive scalar accuracy: overall log-RMSE 1e-9, each-group
log-RMSE 5e-9, and 99% relative-error coverage at 1e-8. The existing 2.4-second
production CPU budget is unchanged. Native invariant evaluation demonstrates
achievability, including the resource gate; no native source or prior
submission is exposed to the agent.

The evaluator validates all 20 group gates and rejects wrong shape, NaN,
constant, biased, and shuffled outputs. Array headers are checked before
allocation. A trusted subreaper reaps the complete prediction process tree,
including orphaned descendants, before reporting CPU consumption. Read-only
system and submission mounts, a label-free query directory, and a network-free
PID namespace isolate every evaluated predictor.
