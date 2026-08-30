# Discovery ledger

Seed: Kos, Poland, Simmons-Duffin and Vichi, arXiv:1504.07997,
particularly equations (2.7), (2.11)-(2.17) and the discussion of isolated
operators and shared OPE coefficients. This package studies explicitly reduced
numerical problems, not new certified islands of the full three-dimensional CFT.

Primary sources inspected: the paper and appendices; SDPB repository README,
Changelog, issue 153 and spectrum rewrite PR 274; PyCFTBoot README and issues;
the earlier local archipelago cone task and its failed 600-second pilot.
Source locations are recorded in sources.json. Prior pilot failure is not
used as evidence for the new tasks.

The following concepts were considered before the fresh tournament:

1. A: Coupled extremal polynomial-matrix spectrum extraction, including
   touching roots, rotating null spaces and residue information. Selected:
   actual follow-up solver failures motivate a numerical quality/resource gap.
2. C: Sparse rank-one mixed OPE moment completion on a discrete spectrum.
   Selected: combinatorial support, coherent radial kernels, PSD rank and
   shared low-state OPE constraints interact; a plain SDP relaxation does not
   certify the requested artifact.
3. E: Adaptive mixed-correlator experiment design under positive spectral-tail
   nuisance. Selected: a fixed query budget forces a design/inference tradeoff.
4. B: Falsify finite-grid matrix positivity with an off-grid negative direction.
   Rejected in this round: a simple narrow polynomial well can make it trivial.
5. D: Predict critical exponents from the published island plot or table.
   Rejected: small data, interpolation/memorization, and unclear held-out truth.
6. F: Repair the old local shifted-cone scanner. Rejected: most work appears
   to be replacing its conic optimizer, not a distinct scientific capability.
7. C: Full three-dimensional exclusion functionals with rigorous spin tails.
   Deferred: credible conformal-block error and infinite-spin certification
   exceed the generation-time validation budget here.
8. A: Joint polynomial sampling/prefactor compression for mixed SDP blocks.
   Deferred: strong potential, but overlaps a neighboring vector-model task.
9. E: Locate island boundaries using a feasibility oracle. Rejected: an
   uncalibrated synthetic contour would measure generic active classification.
10. B: Show spurious exclusion from falsely equating degenerate OPE sums.
    Rejected: the paper itself provides the short algebraic counterexample.

No privileged generators, labels, planted witnesses, prior submissions or
evaluator files are included in the participant allowlist. Fixed objectives
are frozen and hashed before each run. Infrastructure errors are not hardness.
