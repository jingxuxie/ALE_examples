# Model being qualified

The films are parallel, zero-thickness superconducting sheets. All coordinates
are in micrometers. Effective penetration depth is Lambda=lambda_London^2/d,
one half of the Pearl length. The constitutive model is the static London model,
including its conservative variable-Lambda extension. No nonlinear order-
parameter physics, Josephson effects, or finite-thickness regularization is
part of this task.

The stream function g is continuous and piecewise affine on each supplied
triangular mesh. Sheet current is J=(partial_y g, -partial_x g), constant on
each triangle. g=0 on each film's exterior boundary, and g=I_h throughout each
hole and its boundary. Positive I_h circulates counterclockwise. The full outer
footprint is triangulated, including hole interiors; these are not conducting
material. Their constant stream must not generate fictitious current.

`lambdas` specifies the effective penetration depth on each triangle, not a
nodal sample of an unknown smooth function. It can be discontinuous. The state
is the equilibrium of the magnetic field energy plus London kinetic energy
under the applied source and topological constraints. Equivalently the
conservative London relation away from vortices is

    H_z = -curl_z(Lambda J).

Magnetic fields and the magnetic part of the response follow the ordinary
three-dimensional Biot–Savart law for these sheet currents, with all films
included. The sheet has no artificial magnetic core radius. Finite penetration
depth affects the constitutive relation, not the vacuum kernel. At a sheet,
the average of the two one-sided limits defines the principal-value field.
All vector readout points are supplied explicitly. Only the screening response
field, not the externally applied field, is requested there.

The hole fluxoid is flux plus mu0 times the circulation of Lambda J. Imposed
fluxoid is not the same boundary condition as imposed bare magnetic flux.
The response matrix is the derivative of hole fluxoid with respect to the
circulating currents, with no applied field or vortices and all hole currents
independently controlled. Its diagonal is self-inductance. Physical reciprocity
and positivity are useful diagnostics, not permission to alter an inaccurate
matrix after calculation. For the resolved finite-element model, generalized
fluxoids are the quantities conjugate to the hole circulations; contour
postprocessing is a diagnostic and need not define state control.

Units: g and I_h in mA; J in mA/um; H in mA/um; B in mT; fluxoid in mT*um^2;
inductance in (mT*um^2)/mA, numerically pH. In these units mu0=4*pi/10 and
Phi0=2.067833848 mT*um^2.

Applied H_z is supplied as nodal values of a piecewise-affine applied field on
each complete outer footprint, including holes. `vortex_load` gives the already
integrated nodal vortex source in units mA*um; its sum for one positive vortex
is Phi0/mu0. A positive vortex produces positive flux. This avoids an unrelated
ambiguity about rounding vortex locations to the nearest vertex. The JSON
vortex positions document how that source was prepared. A point vortex's
ultraviolet energy is not an output of this resolved model.

Useful independent limits include a kinetic-dominated circular annulus of
inner/outer radii a,b: L approaches 2*pi*mu0*Lambda/log(b/a); and the sheet-current
jump B_above-B_below=mu0*(J_y,-J_x,0) at a point away from edges. Neither limit
is an oracle for a general multi-film driven device.
