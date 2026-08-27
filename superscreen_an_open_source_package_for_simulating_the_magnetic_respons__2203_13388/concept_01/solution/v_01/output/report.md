# Numerical qualification

## Diagnosis and feedback loop

The running legacy development suite produces nearly exact drive linearity and
reported fluxoid constraints, yet its two-hole response has a 0.04197 relative
reciprocity defect. Consequently those first two diagnostics cannot establish
that its state and observation operators represent one conservative device.
The baseline was run before replacement; its raw outputs and process history
are retained in the pilot's screening records.

The replacement uses the resolved stream-function space, with independent
interior values, zero exterior values, and one shared coordinate per hole.
It assembles kinetic energy with the supplied element material values rather
than differentiating a smoothed nodal landscape. Magnetic interactions are
integrals of the triangle currents. Analytic source-triangle potential integrals
and numerical target-triangle integration avoid point-current aliasing; vector
readout uses the same analytic sheet integrals, including both one-sided limits.
All films enter a single coupled energy operator. Fluxoids are conjugate
reactions, and mixed current/fluxoid conditions are imposed on the corresponding
coordinates. Vortex forcing uses the supplied barycentric nodal loads.

## Experiments and revision

After the initial formulation, source integrals were checked against independent
adaptive quadrature. A low target-quadrature rule was then compared with a
higher-order rule and refined to the production setting. Private certification
also compares production assembly with a still higher-order rule, checks
positive definiteness, and checks constraint residuals. These are numerical
checks, not a claim of experimental confirmation of the constitutive law.

The submitted ablation separates low quadrature from omitted inter-film
coupling. On the development stack, coupling changes inductance from 3.15272 to
2.31142 pH, while the mixed-drive field norm changes from 2.60348 to 3.03175 mT.
This is not contradictory: a fluxoid-controlled source changes its circulating
current when its inductance changes. The single-film two-hole control is
unchanged by the coupling switch. Reciprocity is at floating-point precision
without post-hoc symmetrizing the reported response matrix.

## Resources and limits

`scaling.csv` records measured process high-water memory and solve times; the
first run includes JIT compilation. Later timings are warm and should not be
interpreted as cold-process latency. The implementation stores dense triangle
interactions and reuses assembly across drives; memory is quadratic, so it is
not a large-mesh production method. The three supplied configurations generate
distinct raw arrays and the plots are regenerated directly from their tables.

The qualification applies to the supplied piecewise-affine zero-thickness
London model. It does not certify continuum mesh convergence, material
inference, vortex-core energies, finite-thickness physics, or nonlinear
superconductivity. A separate mesh study and experimental comparison would be
necessary for quantitative fabrication decisions.
