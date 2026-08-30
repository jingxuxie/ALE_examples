# Private construction record

Mode A, baseline improvement. This directory and all sibling evaluator and
champion material are generation-only. Never allowlist them to a participant.

Inspected sources: arXiv:2505.02901 and the locally archived paper; official
awietek/xdiag source and recent commits through d7296fa258; issues concerning
sublattice basis construction and inconsistent symmetry-sector energies; and
the prior task's participant/v_02, evaluator/v_02, solution/v_02, and timed-out
fresh_02 submission. These motivate independent full-Hilbert physics checks
instead of trusting symmetry labels or matching a historical reference output.

The old exhaustive solver's spin-half Hamiltonian, Born projections, bridge
kicks, pure-state entropy loss, persistent-regime calibration, and structural
capacity semantics are retained. A new standalone sparse DOP853 engine builds
response catalogs from raw physics. The evaluator uses direct vector evolution
while catalog generation uses independently propagated fundamental matrices.
Small checks additionally build full-Hilbert Kronecker operators and use a
separate exponential midpoint integrator and analytic entropy states.

Three public fleets and six private fleets contain 57 rings in total, including
six L=10 rings. The hidden suite couples seven/eight rings rather than two, with
five ambiguity priors, four persistent regimes, three calibration results,
seven shared sensor designs, ten feedback designs, and order-five outcomes.
Drifting-priors, sector-congestion, and frustrated-bridges families respectively
stress robust posterior decisions, low-probability structural capacity, and
feedback-dependent entanglement after noncommuting kicks.

The task is not another exact-solver implementation: exact conditional response
catalogs and a feasible planner are participant assets. Difficulty lies in
coordinating robust branch-contingent policies with shared manufacturing and
capacity constraints. Every path, including probability-zero paths, reserves
hardware. Greedy local improvements can consume resources needed by another
ring's worst prior, and changing shared design sets changes all admissible
policies simultaneously.

Targets are fixed at 6% core and 3% worst-family improvement before any fresh
agents. No claim of an optimum is made. Offline portfolio artifacts are quality
and feasibility certificates only, not evidence of an online solver satisfying
the 60-second per-fleet limit. Only a separately resource-tested solver could
establish that. No fresh-agent runs or champion-ratchet generations are launched
by this builder.
