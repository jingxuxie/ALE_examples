# Ratchet 1 proposal construction

This directory proposes eight finite-phi4 cases, two in each of four physics
families. Main owns admission, production-baseline runs, calibration, all
public/evaluator edits, and the unchanged numerical scoring constants.

The full g0 champion remains private and byte-identical. The initial
20-case search is retained, including its negative uniform/scaling controls.
At most twelve additional physical requests are allowed in this selection
pass. Reference refinements do not masquerade as new independent cases.

Families are weak-quartic odd-sector critical excitations, unrestricted
symmetry restoration, nonzero-field response, and inhomogeneous/weak-link
critical profiles. Only the symmetry-restoration family has zero-field
unrestricted requests. Explicit odd parity and nonzero fields prevent
reducing the complete proposal to forcing even parity everywhere.

All references use the finite Hamiltonian with projected padded-oscillator
phi2/phi4 operators and the requested bond cap. For fields, a zero-field
parity projection may initialize the teacher, but refinement and all final
measurements use the full original tilted Hamiltonian without a parity
constraint. Exact same-Hamiltonian sector states may improve an unrestricted
reference if the final target-request validation permits them.

The arXiv:1302.5582v3 Eq. 5 / Sec. I D / Fig. 18 mass estimate and the
weak-quartic entanglement motivations in arXiv:2104.10564 are search seeds,
not finite-chain ground-state certificates. The interaction convention
remains lambda4*phi4/24, not the later paper's lambda/4 convention.

`proposal.json` will contain exactly `cases` and `search_summary`; each case
has a budget-free request, family, concept-relative retained reference path,
independently recomputed reference energy, and source case ID. Separate
provenance records retain champion/reference measurements, all source/state
hashes, CPU observations, diagnostics, and honest broad-search counts.
No proposal is an official resource-feasibility certificate.

Selection ranks measured gaps within each family, but retains two distinct
Hamiltonian coefficient profiles rather than admitting basis-only duplicates.
The odd-family margins remain below the preferred ten-times-screen margin;
this is recorded explicitly, not hidden by redefining the screen or discarding
negative controls. The final search uses ten of the twelve permitted additional
requests, in addition to the original twenty comparisons.

Run `verify_proposal.py` from this directory with bytecode disabled to recheck
all sixteen retained states, exact request fields, hashes, and preserved initial
search artifacts. Main still owns production-baseline 6/40 runs, admission,
target calibration, and any actual resource-feasibility claims.
