# Public episode distributions

The hidden suite contains eight independent episodes from each of the four families, shuffled. The family, parameter seed, measurement seed, and episode identifier are not sent to the controller. The initial message is identical in every episode. Hidden seeds are independent of public development seeds. Exact sampling is also public as `model.draw_parameters(rng, family)`; hidden difficulty is experimental inference, not undisclosed distributions.

`signed(a,b)` below means an independent equiprobable sign times a uniform magnitude on `[a,b]`. Unless a dependency is explicitly stated, draws are independent. The coefficient order is IX, ZX, IZ, ZZ, ZI.

| Family | IX | ZX | IZ | ZZ | ZI |
| --- | --- | --- | --- | --- | --- |
| aliasing | signed(3.2,5) | signed(0.5,1.8) | signed(1,2.8) | signed(0.1,1.1) | signed(1,2.5) |
| near_degenerate | signed(1,2.4) | signed(0.2,0.8) | signed(1.1,2.5) | `-IX*ZX/IZ+uniform(-.015,.015)` | signed(.12,1.6) |
| weak_entangling | signed(1,3.5) | signed(.04,.16) | signed(.3,2.2) | signed(.02,.12) | signed(.2,1.8) |
| nuisance_decoherence | signed(.7,3.8) | signed(.25,1.5) | signed(.3,2.4) | signed(.15,1.1) | signed(.2,2) |

For near_degenerate, resample IX, ZX, IZ and the ZZ perturbation together until `abs(ZZ)<1.2`. This makes the two conditional target rotation magnitudes nearly equal; it does not identify the control states with each other. Signed product-state readout retains information about the distinct rotation axes.

In the first three families, visibility is uniform `[.91,.99]`, readout contrast `[.9,.95]`, bias `[-.025,.025]`, and decay `[.008,.045]`. In nuisance_decoherence these are `[.78,.86]`, `[.78,.85]`, `[-.045,.045]`, and `[.1,.16]`. The inclusive global box in `config.json` is the allowed estimate box; the family laws give additional public distributional information.

High frequency produces finite-design aliasing; near-degenerate conditional frequencies complicate axis separation; small nonzero entangling rates require absolute precision; lower visibility and stronger decay alter useful experiment durations. Continuous time choices and trusted Pauli phase references avoid an intrinsic discrete-time alias or sign equivalence.
