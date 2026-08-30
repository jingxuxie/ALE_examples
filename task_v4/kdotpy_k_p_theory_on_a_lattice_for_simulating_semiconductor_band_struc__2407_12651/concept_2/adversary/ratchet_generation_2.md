# Generation 2: simultaneous calibration sensitivity

Fresh generation 1 passed every original condition (score 100, worst-family 100) in 1671 seconds. Its frozen artifact and evaluation are in champions/generation_1. This is a solved generation, not a retained hardness result.

A preregistered 2400-point private sweep changed coefficients within a radius-0.02 product box, divided among mass/offset, dispersion, hybridization, and mixed families. Respective plateau failures were 48/600, 51/600, 40/600, and 232/600. Refined 129x129 evaluations confirmed worst plateau spreads 0.01534, 0.02048, 0.01556, and 0.03350. The complete responses remained 1 to floating-point accuracy, the refined gap certificates exceeded 0.53, and the worst mixed case retained adequate optical coupling. These are spectral-window cancellation failures, not gap closures or underresolved full response.

The second generation retains all nominal goals, coefficient support, normalization, and response definitions. It raises the finite perturbation audit radius to 0.02 and adds 256 fixed, hidden, uniformly sampled simultaneous perturbations from exactly the public box. The finite nature of this audit is explicit; no continuum guarantee is claimed. The held-out set is frozen before the fresh challenger is launched. The new task is still a counterexample to a specified convergence heuristic, not a claim about a kdotpy theorem.

No previous fresh submission or private witness is exposed to the new agent. The weak baseline remains unchanged. Acceptance still requires every condition, not an average over perturbations. The old champion is replayed on the new task before launch. A passing construction for generation 2 is unknown until actually checked.
