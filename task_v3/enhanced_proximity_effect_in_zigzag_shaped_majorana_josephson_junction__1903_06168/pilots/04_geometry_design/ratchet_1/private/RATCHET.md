# Ratchet 1: improve a working long-period optimizer

This is the first ratchet of concept 04, not a fifth concept. No initial scores or initial participant files change.

## Demonstrated gap

The frozen initial executable was run, without edits, at the largest published feasible period: 1940 nm, 66-by-97 sites, 25,608 BdG degrees of freedom. It completes in 1146.22 seconds under the original 1200-second/two-core budget. Its geometry and topology are valid. On the three discovery scenarios it reaches R=0.150396878555 meV, versus the original weak R=0.076664313072 and unmodified author R=0.175688437735. The original normalization gives **0.744591943976**.

The low-field gap nearly matches the author reference (0.147635 versus 0.150540 meV). The middle and higher-density points remain substantially deficient (0.182986 versus 0.226919, and 0.142940 versus 0.225052 meV). Its search completes 39 initial geometries and 59 after refinement, without improving the regional best during that refinement. This is an achieved but inadequate physical optimization, not a missing output, dependency problem, timeout, or loss of topology.

The observed failure is clustered in large-period robust geometry optimization, especially its higher-density/field branches. Limited profile search and the expense of additional full-scale evaluations are supported bottleneck hypotheses. No unique microscopic cause or impossibility theorem for generic methods is claimed.

## Changes

- Focus the mission on the demonstrated long-period bottleneck, rather than retesting already solved smaller cells or adding unrelated disorder/constraints.
- Publish the achieved geometry and its working three-file optimizer as a usable starting point. The missing capability is further physical improvement, not reconstructing the original solver.
- Keep the same Hamiltonian, grid spacing, full 51-momentum metric, fabrication checks, topology gate, and runtime budget.
- Make every request's exact operating points public in its input. This removes the possibility that a low score merely reflects guessing undisclosed sampling points.
- Measure improvement relative to the now-public achieved layout; retain the same unmodified author epoch-800 geometry as the private strong solution. This is the public-baseline improvement route, not a numerical-tolerance ratchet.

The author reference improves the discovery robust gap by about 16.8% over the achieved layout. Its high-density gap improves much more. These are physical energy differences, not tighter residual tolerances.

## New held-outs and gates

Three interior operating triples are fixed in `reference/source_manifest.json` before calibration or a confirmation attempt. None equals the inspected discovery triple. They remain in the published physical domain. No case may be dropped or resampled merely because the author reference loses. The supplied source design must remain feasible and have a strictly positive improvement anchor for every case.

The public example is the inspected discovery request with no strong labels. The private held-outs are delivered as ordinary unlabeled requests, including their exact scenario lists. No old attempt history, model transcript, or source optimizer is public; only the explicitly published baseline code and layout are carried forward.

Anti-compression is rechecked: a forward eigensolver does not choose a manufacturable improved contour. The task still combines constrained geometry search, topological/robust performance, and an evaluation-cost bottleneck at the source's largest cell. The old optimized numerical strategy is now public, so rediscovering that strategy alone cannot establish hardness. A fresh confirmation is required; source-grounded existence of a better mask is not sufficient.

Accept only if all reference/public-completeness gates pass, the independent fresh confirmation has core score below 0.70 with a substantive unsolved optimization component, and worst-family results support that conclusion. Scores at or above 0.90 are solved. A moderate confirmation permits at most one further genuine ratchet; merely shifting anchors or tolerances again is not sufficient.
