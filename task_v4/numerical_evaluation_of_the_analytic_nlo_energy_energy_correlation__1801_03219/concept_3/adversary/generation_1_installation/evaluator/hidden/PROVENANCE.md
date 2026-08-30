# Private scientific provenance and design rationale

Do not distribute this directory or the adversary directory to participants.

## Seed and deliberate departure

Lance J. Dixon, Ming-xing Luo, Vladyslav Shtabovenko, Tong-Zhi Yang, and
Hua Xing Zhu, *The Energy-Energy Correlation at Next-to-Leading Order in QCD,
Analytically*, arXiv:1801.03219v2, revised January 11, 2018, subsequently
Phys. Rev. Lett. 120, 102001 (2018). The authoring process checked the primary
paper's equations (1) and (2) and the sentence explicitly retaining self-pairs.
Primary reference: `https://arxiv.org/html/1801.03219v2`.

Equation (1) defines an energy-weighted ordered-pair angular distribution;
equation (2) gives unit integral after normalization by the total cross section.
Here a single event has total energy one, and its corresponding normalized
atomic measure replaces the cross-section average. This task borrows that
observable, not the NLO coefficients, polylogarithmic formulas, integration
algorithms, or perturbative final-state multiplicity. The constructed 192-particle
event is a kinematically admissible synthetic massless energy flow, not an NLO
QCD spectrum. Zero-weight directions are absent particles.

## Exact reduction and endpoints

Let the pair count be 512, the direction count 1024, and the integer sum 128.
The full direction weights repeat the pair sequence twice and divide by 256.
For a full directed separation, the integer pair-product numerator is twice
the pair autocorrelation; its denominator is 65536. Thus directed bin masses
are the prescribed autocorrelation divided by 32768. Folding opposite directed
separations into the same cosine angle doubles interior bins, but does not
double the zero-angle or antipodal bin. Each endpoint has mass 384/65536.
The independent audit reconstructs both histograms from all nonzero ordered
particle pairs, also assigning bins from their actual trigonometric dot products.

Antipodal equality enforces exact momentum cancellation symbolically and gives
massless momenta by construction. Integer checks are authoritative; floating
trigonometry is used only as an independent diagnostic. The angular and directed
histograms have exact rational total mass one and zero first cosine moment.
Autocorrelation symmetry makes the complete folded angular histogram equivalent
to the complete published autocorrelation; no limited-moment surrogate is used.

## Fixed feasible target and honest difficulty

Keep the user's proposed 1024 directions, 64 ones, 32 twos, and 416 zeros.
No size or density adjustment is based on a solver result. The private generator
draws one cyclic independent support using a uniform gap composition and random
rotation, then randomly permutes the prescribed nonzero labels. Its entropy
comes from SystemRandom; no reproducible public seed or planted coordinates are
published. Feasibility is checked before freezing. A one-shot, no-overwrite
manifest records the target bytes, digest, timestamp, and private witness hash.

The task is finite nonconvex inverse design: participants must construct a
ternary, separated cyclic sequence with a prescribed quadratic autocorrelation.
The target is known feasible, but uniqueness is neither claimed nor required.
Rotations, reflections, and any homometric feasible alternatives are valid.
No witness identity is tested. Fourier magnitudes are public consequences of
the target, and specialized reconstruction methods are legitimate approaches.

Only bounded local-search calibration is performed in authoring. Its failures
do not establish intrinsic hardness or failure of a one-hour agent. The main
session owns the two fresh attempts and any tournament decision. Never label
this hard-verified solely because an annealing baseline fails. The target stays
fixed throughout those attempts; any future redesign needs a new generation
and a new freeze before fresh attempts, not a changed grader behind an attempt.

## Audit independence and privacy limitations

The grader accumulates occupied pair products. The private audit separately
uses dense cyclic products and direct full-event geometry, without importing the
grader's correlation helper. It also checks the baseline's integer update formula
against full recomputation, each individual lag's enforcement, malformed inputs,
cyclic boundary handling, and static-only evaluation in subprocesses. This is
computational independence, not independent-human or independent-agent review.

Hidden directory permissions are defense in depth only. Same-user agents must
receive a true allowlist containing participant/ and one empty attempt directory;
they must not see evaluator/, adversary/, status.json, private provenance, or
the plant. Do not expose this entire concept directory to a solver. The checker
never reads the plant during grading; only target.json and its digest manifest
are needed. Runtime/resource scores describe bounded checking of static input,
not unobservable solver synthesis costs.
