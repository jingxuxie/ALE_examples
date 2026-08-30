# Asset contract

Candidate index is list position. `germ` is executed left to right and repeated
`repetitions` times. Preparation indices select +X,-X,+Y,-Y,+Z,-Z; measurement
indices select X,Y,Z. These preparation/measurement axes are externally
calibrated, not additional noisy gates. The two unknown readout parameters are
shared across axes. All gate errors are in the laboratory frame, so there is
no unobservable gauge rotation in the specified parameterization.

The first nine parameters are additive rotation-vector offsets to X(pi/2),
Y(pi/2), and I. The next three are nonnegative depolarizing decay rates per
gate application. The last two are readout bias and visibility. Exact operation
and family-sampling definitions are in `workspace/physics.py`.

`development.npz` stores `features[scenario,candidate,parameter]`, `parameters`,
`families`, `nominal_features`, `baseline_risks`, and per-batch `costs`. A feature
is a probability derivative in the scaled parameter coordinates, divided by
sqrt(p*(1-p)). The information is the sum of 64*batches times feature outer
products plus 1e-10 times identity. A-risk is the trace of the leading 12-by-12
block of its full inverse, retaining readout nuisance correlations. The tiny
ridge is solely a numerical convention, shared by public and private scoring.

In this generation, `champion_intact_risks` and `champion_loss_risks` are
the current baseline's intact and worst-three-circuit-loss risk vectors.
`baseline_risks` aliases its intact risks. These arrays contain development
points only. A loss removes every shot belonging to a selected circuit, without
refunding cost or allowing reallocation. The worst lost set is chosen separately
for each operating point. If fewer than three circuits are selected, all are lost.

`core_score` = mean(champion intact risk) / mean(submitted worst-three-loss risk).
The same ratio is calculated separately in each regime; `worst_family_score` is
the minimum of those six ratios. Passing requires core >=0.25 and every regime
>=0.20. The intact guard is mean(submitted intact risk) / mean(champion intact
risk) <=1.20. Thus the primary objective is a fourfold overall and fivefold
per-regime variance-risk budget, not merely a percentage improvement over a
possibly singular lost-record baseline. Larger primary and family scores are
better. Evaluation additionally reports ordinary loss-risk reduction, execution
cost, intact risk ratio, and the worst lost sets. No numerical comparison slack
is added to the stated thresholds.

All six regimes have equal weight. The 600 hidden operating points use the
disclosed sampler, with no new noise mechanism or circuit family.
`workspace/resilience.py` implements exhaustive loss-risk evaluation.
