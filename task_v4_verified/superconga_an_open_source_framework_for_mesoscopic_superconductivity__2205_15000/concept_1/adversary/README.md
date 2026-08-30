# Builder controls and adversarial checks

No fresh agent sessions are used. The generic multistart control uses only
L-BFGS-B from the supplied start and independent random phase perturbations.
It does not use vortex detection, holes, surgery, references, or case IDs.
Its completed starts and all local-minimum energies are retained in `attempts`.
The initial physical-lattice pilot was rejected because this control passed;
the pilot and its measurements remain private for auditability.

`evaluator/test_model.py` checks random directional and coordinate finite
differences, independent energy/gradient agreement, arbitrary local gauge
transformations, actual physical plaquette flux, positive stiffness, omitted
hole links, the known uniform zero-field minimizer, and malformed NPZ outputs.
`evaluator/test_evaluator.py` tests score clipping, regression and stationarity
failures, invalid/missing cases, family weighting, fake energy metadata, compressed
bombs, and corrupt references. `evaluator/test_sandbox.py` exercises the real helper.

The private algorithm in `champions/in_budget` is executable code only. It is not
a lookup table, never reads hidden fields, and is evaluated through the identical
sandbox/resource path used for untrusted submissions. Stored witness feasibility
and a passing in-budget executable are explicitly separate results.
