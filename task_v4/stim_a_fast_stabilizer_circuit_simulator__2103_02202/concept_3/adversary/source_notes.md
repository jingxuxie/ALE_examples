# Generation-time evidence and caveats

The eight-concept rationale is copied from the main session's parent `DISCOVERY.md` to `concept_research.md`. Only concept_3 is implemented here. No fresh agent is launched, and no empirical participant hardness is claimed.

Primary sources inspected:
- https://arxiv.org/abs/2103.02202 — Stim, including signed tableaux, independent gate checks, and motivation for circuit search.
- https://github.com/quantumlib/Stim/wiki/Stim-v1.13-Python-API-Reference — exact Clifford synthesis versus state-only synthesis; graphlike and heuristic fault-search limitations.
- https://github.com/quantumlib/Stim/releases/tag/v1.14.0 — flow generators, time reversal, feedback and noise fixes.
- https://github.com/quantumlib/Stim/releases/tag/v1.16.0 — stimflow and further signed-flow/error-explanation fixes. Authoring here deliberately uses the available pinned 1.15.0, not an unpinned latest version.
- https://github.com/quantumlib/Stim/issues/391 — historical decomposition/search inconsistency.
- https://github.com/quantumlib/Stim/issues/1004 — repeated-circuit search cost.
- https://github.com/quantumlib/Stim/issues/1098 — remnant logical-label audit request, not a proven bug.
- https://arxiv.org/abs/2302.02192 — hardware-constrained time-dynamic circuit design.
- https://arxiv.org/abs/2307.10147 — tangled schedules and native circuit fault mechanisms.
- https://arxiv.org/abs/2604.09797 — morphing circuits, boundary/schedule optimization and circuit-distance pitfalls.
- https://arxiv.org/abs/2404.06545 — experimental design of noise characterization.
- https://arxiv.org/abs/2606.11496 — syndrome-based noise estimation and logical-label identifiability limitations.

Concept_3 asymmetry: the author privately knows a compact native circuit and its generation entropy; participants see only its signed target, native graph, budgets, independent checker, and a generic elimination circuit routed to the grid. The private native witness proves feasibility, not synthesis difficulty or optimality. Acceptance compares every signed X and Z generator and counts explicit schedule resources. It does not check only the prepared stabilizer state or unsigned matrix. Generic synthesis plus routing is intentionally supplied as a valid but inefficient baseline, not withheld as an artificial prerequisite. No Stim package, source, circuit-generation seed or compact witness is exported.
