# Constrained thermal free energy

Predict the angular Helmholtz free-energy landscape of interacting classical magnets at finite temperature. Each case contains thousands of unit spins with competing bulk, surface, cubic, or interface anisotropies.

For every requested angle, return the equilibrium total y-torque per spin and the free-energy difference per spin relative to angle zero. The direction of the total magnetization is constrained; its magnitude must remain free to fluctuate. Mean internal energy is not a substitute for free energy.

Implement `solve.py CASE.json OUTPUT.json` in your submission directory. NumPy archives are also accepted as specified in `input/FORMAT.md`. You may compile native helpers. The supplied local-energy and unconstrained-Monte-Carlo utilities are starting points, not a constrained sampler. The baseline is an uncontrolled coherent-rotation approximation.

Evaluation combines torque and free-energy accuracy continuously relative to that baseline, reports mean and worst-family performance, and records runtime. Read `input/FORMAT.md` for the complete physical, execution, and output contract.
