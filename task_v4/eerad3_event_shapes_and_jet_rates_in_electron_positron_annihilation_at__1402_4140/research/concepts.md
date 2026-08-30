# EERAD3 hardness-discovery shortlist

The primary seed is arXiv:1402.4140, especially separate multiplicity channels,
double-unresolved phase space, classical observables, and numerical subtraction.
The official 1.0 archive and the official releases repository were inspected.
The repository HEAD inspected is 36ebb48299a6f8299d7eb9ccdc3a9b4ac7d1efe9,
with seven public commits through release 2.0.0. Public issue and merge-request
API responses were empty. The 2025 follow-up is arXiv:2503.20610v1.

Eight concepts considered before building:

1. A: improve native NNLO integration across colour structures and rare bins.
   Strong science, but trustworthy low-noise scoring needs an expensive campaign.
2. D: predict a native five-parton leading-colour matrix-element kernel across
   generic, soft, collinear, doubly collinear, and triple-collinear phase space.
   Selected: exact source-native held-out labels, no artificial fitted physics.
3. B: falsify six-observable sufficiency with resolved five-parton event pairs
   whose classical shapes agree but whose five-jet transition differs.
   Selected: continuous constrained inverse geometry, independently checkable.
4. F: repair native antenna momentum mappings in hierarchical unresolved limits
   while preserving physics, ordinary-point behavior, and resource efficiency.
   Selected: independent high-precision and physical-invariant verification.
5. C: construct minimal angular quadratures for correlated double-unresolved
   spin cancellation. Rejected: too close to a standard harmonic cubature rule.
6. E: adaptive colour-channel allocation with heavy-tailed native measurements.
   Deferred: valid simulator calibration requires an additional native campaign.
7. A: improve prior covariance-aware campaign allocation. Rejected: earlier
   task used supplied Fisher matrices; old 600-second missing-submission timeout
   is not strong scientific evidence of one-hour hardness.
8. F: reimplement histogram normalization and scale envelopes. Rejected: mostly
   direct implementation of complete formulae and file-format conventions.
9. B: find renormalization-envelope undercoverage. Rejected: could reduce to a
   simple scan of supplied coefficient tables rather than substantive discovery.

Only concepts 2, 3, and 4 above are built, as concept_1, concept_2, concept_3.
All source solvers, hidden cases, generator code, old attempts, and validation
artifacts remain outside participant directories and fresh-agent allowlists.

Prior task inspection: the v1 fresh solver scored 100; v2 had no solver after
600 seconds. Its finite allocation problem is not reused as physics truth.
