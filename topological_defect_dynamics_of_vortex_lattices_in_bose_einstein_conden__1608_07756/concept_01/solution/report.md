# CPU migration acceptance investigation

The baseline's unit calibration fails for the sign of an isolated antivortex and
for uniform-flow kinetic partition, although phase-only density preservation
passes. Inspection then separates three independent problems: real exponential
attenuation of the nonlinear term combined with renormalization can hide incorrect
dynamics; density-minimum detection confuses phonons and phase singularities;
fixed-neighbor/self-product statistics cannot measure topological disorder or
spatial orientational correlation. Axis-wise unwrapping is not a reliable global
current reconstruction in a multiply connected phase field.

The repaired propagation uses conservative symmetric directional exponential
steps with rotation included in the directional Hamiltonians and midpoint drive
evaluation. This is not the only valid integration strategy. Spectral current
derivatives and longitudinal/transverse projection give consistent lab-frame
kinetic energies. Signed plaquette winding and local complex-zero refinement
separate holes from vortices. Neighbors are constructed from guarded,
component-aware material geometry before selecting bulk measurements.

We first ran the supplied analytic checks, inspected their failures, replaced the
affected stages, and reran them successfully. We then ran the complete control,
vacancy, reversal and cluster campaign. Finally we repeated it at half the time
step and with the guard-region construction deliberately removed. The latter is
an analysis-method ablation, not a different physical intervention: it demonstrates
how a plausible boundary convention changes the inferred defect population.
The primary and half-step runs assess temporal sensitivity without changing
physical inputs. Exact measured contrasts are in claims.json and the full tables.

The end-of-window vacancy-minus-cluster far-bin correlation is positive, supporting
greater retention of orientational order after localized erasure in this prepared
state. The reversal lies between these interventions in the endpoint comparison.
The cluster's spatially broad non-sixfold population and much lower correlations
support substantially greater lattice disorder; merely counting density minima
would not establish that conclusion. The control is important because an
imperfectly stationary finite-grid initial state may itself evolve.

Importantly, this is relative retention, not a recovery of an almost perfect
background lattice after erasure: final far-bin order is about 0.259 for the
vacancy versus 0.994 for the control and 0.039 for the cluster. Thus this smaller,
shifted condensate does not justify an unqualified transfer of the strong
quasistability/order claim. Temporal refinement leaves this discrepancy in place;
the guard ablation changes its magnitude but does not explain away the primary
state's actual loss of orientational order. This distinction is a central
scientific outcome of the migration investigation.

The saved fields, rather than just reported counts, are the reproducibility
record. The plotting source is workspace/render.py: the first figure uses
results.csv time/g6_far/defect_radius; the second uses the three tables' n5/n7 and
scaling.csv wall_seconds. All reported timing/memory rows are measured end-to-end.

This is a bounded dimensionless reconstruction, not a numerical reproduction of
every physical parameter or the full six-second observation in the original
research. Temporal refinement is not a proof of continuum spatial convergence.
The public state has only several dozen measured cores; annular and split-domain
tests validate the port's measurement contract but do not establish universality
of the vacancy stability claim. No indefinitely stable vacancy, universal melting
threshold, or statistical population confidence interval is inferred from one
deterministic initial state. Rotating-frame energy conservation is inapplicable
under the prescribed moving drive; norm conservation remains applicable.
