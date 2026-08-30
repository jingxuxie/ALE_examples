# Same-physics extension protocol

`python evaluator/hidden/extend.py --seed 104729 --count 16 --output proposals.json`
generates a reproducible wider parameter sweep. Its mass, quartic, spring, basis,
cutoff and cap ranges stay inside the advertised family envelope. Nonuniform
mass/well profiles, positive weak links, and small explicit fields test real
metastability and conditioning; no antiferromagnetic/frustrating sign convention
is introduced. Fields are exactly zero for fixed-parity requests.

These are **proposals, not calibrated cases**. Do not merge them silently into the
frozen evaluator, use a hidden-case lookup, or reuse old normalization energies.
Before a champion ratchet, main must freeze a new version/target, independently
calibrate each proposal with retained cap-compliant tensors, run a stronger or
independent check where feasible, and evaluate the same submitted algorithm under
the same sandbox/time rules. Keep the original suite report separately.

Record per-case and per-budget energy/regret, parity, max bond, CPU, validity,
reference sweep trajectory, and init dependence. `diagnostics.py` also reports
site means, local cutoff-edge populations, and nearest-neighbor correlations.
Large init dependence suggests metastability; a missed sign of tiny field with
different well selection is physical, not a numeric-ID puzzle. Large top-level
populations flag oscillator truncation/conditioning; the fixed truncated
Hamiltonian still defines the objective. Failed parity identifies sector leakage.
Slow early improvement with later recovery is a budget/convergence issue.

Teacher energy feasibility does not certify resource feasibility. Only a genuine
algorithm or legitimate non-lookup portfolio passing the frozen evaluator may be
called a known full passing solution. Otherwise retain `hard_open_candidate`.
