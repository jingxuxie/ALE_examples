# Final manufacturing-corner ratchet

Generation 2 is scientifically solved. Although its fresh agent timed out before
copying the witness to the required filename, the unchanged pre-deadline
`final_candidate.json` passes every generation-2 condition. That operational
failure is not counted as scientific hardness.

The promoted candidate was tested on 2,400 independently generated corners of
the same coefficient box, grouped by physical terms. It fails 38 of 600 mixed
corners. The worst failure survives refinement from mesh 41 to 129: the three
window responses have spread 0.01464514, versus the unchanged 0.009 robust limit.
The complete response remains 1, the independent Chern number is 1, and the
certified gap exceeds 0.495. This is a sensitivity of spectral-weight
cancellation, not a topological transition or inadequate quadrature.

Generation 3 keeps the model, 25 control variables, coefficient bounds,
perturbation radius 0.02, and all numerical witness thresholds. It supplements
the existing finite audit with complete corners of the three disjoint physical
groups and 512 independently drawn full simultaneous corners. These private
probes are generated and frozen before a fresh agent starts. They are not a
claim to verify the entire continuous box. No new target is inferred from the
forthcoming submission. A passing implementation is not yet known.

Evidence: `champion_generation_2_corner_probe.json`; the unchanged generation-2
candidate and score are preserved in `../champions/generation_2/`.
