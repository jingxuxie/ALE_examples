# Private generation-2 rationale

The previous completed champion is valid and generation 1 is solved. Its exact
unmodified JSON is archived in `previous_generation/champion_witness.json`; the
root `champions/generation_1/witness.json` is untouched. The public baseline is
that champion with all weights scaled to the new row L1 bound ln(999).

This generation changes exactly one scientific constraint: every conditional
outcome probability must now be at least 0.001. No entropy, correlation,
degeneracy, perturbation, or beta-window gate is added. It tests false convergence
under an explicit operational exploration floor, not retroactive validity.

The completed champion's floor sweep and construction-class variance lower-bound
proof are archived privately in `previous_generation/`. The existing method is
obstructed: four unbiased independent free spins and independent backbone copies
on a ground-state subcube obey Var(R) >= 56 beta^2 epsilon(1-epsilon), exceeding
0.05 at epsilon=0.001 and beta>=1. This is NOT a no-go theorem for general VANs.

No passing witness for the new contract is known. General attainability is
UNKNOWN. The user explicitly accepts `hard_open_candidate`. The archived
perturbation and entropy discussions are evidence only, not participant hints,
additional acceptance conditions, or claims of reference solvability. No fresh
agent or additional private feasibility search is launched by this build.
