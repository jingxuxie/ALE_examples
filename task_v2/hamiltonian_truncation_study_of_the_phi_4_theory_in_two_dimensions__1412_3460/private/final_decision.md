# Final decision: rejected

One concept was built after screening five source-derived workflows. The
known-good solution passes: overall 0.9716603, core 0.9700000, and all five
families 0.9700000. Its matrix elements agree with the official ancillary code
at roundoff; Gaussian and oscillator checks pass; all ten raw-cutoff scans
obey variational ordering. The participant packet is complete, anonymized,
and independently runnable without access to the paper or solution.

## Empirical screen

A completely new allowlisted ultima-alpha session used 1840.743 seconds
(30 minutes 40.743 seconds), did not time out, and left participant files
unchanged. It receives only participant/v_01 and attempts/v_01 plus system
runtime files. The private target file and reference are never mounted in
the agent or submission replay sandbox.

The submission scores 0.9833815 core and 0.9658331 overall. Family scores are
Gaussian 0.9700000, periodic quartic 0.9913388, antiperiodic quartic 0.9986454,
source-broken 0.9983264, and inhomogeneous 0.9946239. Hidden replay takes
69.099 seconds and peaks at 464.277 MiB. Public replay takes 46.788 seconds.
All eight evidence consistency checks pass. The lower overall score than
the reference reflects genuine runtime/memory pressure, not worse spectra.

The transcript and submitted report establish substantive scientific success:
the agent diagnoses the scalar-shift gap cancellation, the finite-circle
normal-ordering error, and missing reflection sectors from an all-ones Krylov
start. It independently constructs general polynomial oscillator matrices in
C++, matches the public archives at roundoff, implements finite-volume Wick
spectral tails, and compares local and spectator-dependent corrections. It
rejects a reduced Ritz shortcut after a controlled error check, uses larger
generated bases and shell extrapolation, validates the result at a still
higher cutoff, and reports limitations without claiming a critical point.
Its seven tests, trimmed/renamed replay and coupled experimental deliverables
show a genuine run–diagnose–revise–rerun workflow rather than an output-schema
shortcut.

## Why the task is not retained

The mandated >=0.90 core rule is decisive. The physically distinct branches
are still handled by one generalized normal-ordered polynomial Fock engine,
local UV-tail treatment and higher-cutoff extrapolation. The agent can
generate missing states cheaply enough to bypass the intended low-space
research bottleneck. No substantive capability defeats it. Calling this
frontier-hard because its code is long, its physics is specialized, or its
report contains many experiments would contradict the empirical result.

No redesign, stricter threshold, extra edge cases, or post-screen target
change is made. The scorer, hidden campaign and target hashes match their
pre-screen snapshot. The other four independently enumerated concepts were
already rejected before construction: critical-coupling fitting lacks five
independent real families; spectral-measure reconstruction collapses to a
Schur/shell calculation; modernization exposes the complete solution; and
resummation lacks sufficient original artifacts. None justifies constructing
a nominally different second pilot in violation of the source/shortcut gates.
The bounded search therefore ends with
`paper_did_not_yield_frontier_hard_task`, not a retained candidate.

## Infrastructure accounting

The first launch waited on inherited stdin before starting the model. It was
stopped after 103.298 seconds, preserved under `concept_01/infrastructure`,
and excluded from hardness evidence. Closing stdin fixed the launcher; the
valid run used a new session and received the full one-hour allowance. This
was not a task redesign and did not change participant content or grading.
