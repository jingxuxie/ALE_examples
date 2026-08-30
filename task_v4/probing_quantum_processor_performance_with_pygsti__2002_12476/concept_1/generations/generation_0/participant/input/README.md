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

Overall reduction is 1-mean(submitted risk)/mean(baseline risk). Regime reduction
uses the corresponding regime's means. All six regimes have equal weight.
Hidden operating points are independent draws from the disclosed sampler;
no undisclosed noise model or circuit family is introduced in this generation.
