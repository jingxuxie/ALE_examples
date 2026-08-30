# Current evaluation regime

The current three-case family consists of connected perforated grains with
48–64 holes, narrow superconducting bridges, physical near-half-flux hole
solenoids, and small geometry/material/flux variations. The energy and input
schema are unchanged. Lattice dimensions are approximately 90–140 sites per
side; do not specialize to one particular geometry or size.

The initial field in each test input is already converged and is the frozen
baseline. The source of that field was a previous, successful low-energy solver,
which is supplied as `baseline/champion.py`. The checker independently validates
the output's energy and gradient; neither winding labels nor a particular search
method are required.

The two development cases and their numeric targets are independent of the
hidden scoring cases. The prescribed vector potential
is allowed to be nonuniform and to enclose flux in holes; it is part of each
fully specified input, not an unknown latent quantity.
