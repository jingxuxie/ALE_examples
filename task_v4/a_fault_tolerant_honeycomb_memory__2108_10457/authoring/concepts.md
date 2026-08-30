# Concept selection record

Seed: A Fault-Tolerant Honeycomb Memory, arXiv:2108.10457v2.
Official source: Strilanc/honeycomb_threshold, commit d71737d.

Eight candidate concepts were considered before building:

1. A — Improve modern two-pass correlated matching on unseen native circuit samples, including separate observables and circuit-noise families. Strong baseline, coset degeneracy, and constrained inference make this more than turning on correlation support. Selected for concept 1.
2. B — Find certified low-weight, noise-robust failures of a correlated matching reliability claim on source-native honeycomb detector models. Rejected after research: a meaningful robust gap was not established, and published boundary counterexamples would reduce to copying known witnesses.
3. D — Predict held-out finite-size logical error rates from actual paper experiment records. Structured extrapolation, binomial observation uncertainty, circuit regimes, and observable asymmetry distinguish this from implementing a published fit. Candidate for concept 3.
4. C — Construct a local-Clifford supercell for fixed lab-frame, heralded phase-erasure profiles. Selected for concept 2: exponentially many joint design choices, exact GF(2) logical-ambiguity certificates, and a known physical motivation in bias-tailored Floquet codes. The schedule remains fixed; this is not an unheralded EM3 threshold claim.
5. E — Allocate calibration experiments to identify correlated two-body measurement noise. Attractive, but an arbitrary noise-parameter family risks making unidentifiable parameters masquerade as hardness.
6. F — Repair gauge/detector tracking across arbitrary Floquet initialization and termination phases. Rejected as too close to reproducing the official compiler and potentially solved by a standard stabilizer elimination routine.
7. A — Optimize honeycomb aspect ratios under anisotropic operation costs and logical failure. Rejected because the available parameter grid admits routine enumeration rather than a substantive inference gap.
8. D — Infer teraquop qubit counts from near-threshold small-distance data. Rejected as a standalone task because labels in the paper are themselves extrapolations, not independent ground truth.

Only three concepts will be built. Fixed targets, hashes, baselines, and first-tournament records are stored per concept. Generator-only assets, source history, and held-out observations are not participant assets.
