# Model and execution contract

## Artifacts and precision

`checkpoints/{single-L32,single-L64,range-L32}.npz` contain unmodified trained
float32 arrays, exported without pickle. Promote them for inference if useful.
`models.json` records every array shape, coupling, and checksum. No training,
sampling, action evaluation, or parameter fitting is requested. Output real
finite float64 arrays. All lattice boundaries are periodic; all sums below are
ordinary sums, not volume or orbit averages. The supplied integer `orbits`
array is authoritative: do not reconstruct its numbering from radial distance
or assume equal squared distance means equal orbit.

| Model | Source side S | Field features F | Coupling | w shape |
|---|---:|---:|---|---|
| single-L32 | 32 | 50 | 4.572 only | (153,20,20) |
| single-L64 | 64 | 50 | 4.398 only | (561,20,20) |
| range-L32 | 32 | 300 | [4,6], inclusive | (153,20,1000) |

There is no trained conditional L64 checkpoint. Conditional L64 requests use
the explicitly defined transfer profile of range-L32, without retraining.

## Trained contraction

Let time t be in [0,1]. Its 21 features, in storage order, are

`q(t) = [sin(2*pi*k*t) for k=1..10, cos(2*pi*k*t) for k=1..10, 1]`.

At a site with scalar field u, the F features are

`h(u) = [sin(phi_freq[r]*u) for r=0..F-2, u]`.

The last feature is linear, not a constant or another sinusoid. There is no
nonlinearity after convolution and no bias.

For fixed models, set `A = freq_superpos / F`, `T = time_superpos / 21`,
`a = T @ q(t)` and `C[o,c] = sum_d w[o,c,d]*a[d]`.
`A` has shape (20,F), `T` has shape (20,21), and C has shape (O,20).

For the conditional model, define 50 centers `z[r]=r/49`, normalized coupling
`s=(lambda-4)/2`, and

`beta = log(1 + exp(width_factor))*49`

`g[r] = exp(-beta*(s-z[r])**2) / sum_j exp(-beta*(s-z[j])**2)`.

The exponent contains beta, not beta squared. This is smooth normalized
Gaussian interpolation, NOT piecewise-linear interpolation, a nearest-knot
lookup, or a mixture of separately evaluated flows. There is no clamp or
truncation at neighboring centers. The trained scalar width is shared across
all 50 Gaussians and all occurrences of g.

Contract all three independently trained lambda-dependent tensors:

`A[c,r] = sum_l freq_superpos[c,r,l]*g[l] / 300`

`T[d,k] = sum_l time_superpos[d,k,l]*g[l] / 21`

`a[d] = sum_k T[d,k]*q[k]`

`W = w.reshape(O,20,20,50)` in C order, with lambda the fastest last index.

`C[o,c] = sum_d sum_l W[o,c,d,l]*a[d]*g[l]`.

The same g enters A, T, and C; its normalization and all three dependencies
matter to the coupling derivative. `phi_freq` is trained but not conditional.

## Geometry and transfer

Expand the native kernel as `K[j0,j1,c]=C[orbits[j0,j1],c]`.
The native profile requires L=S. Its tap origin is `(S//2,S//2)`.
The kernel has D4 orbit sharing on the source periodic lattice; orbit zero
is the native zero-displacement tap. Reflections at even extents include the
periodic wrap, not merely array reversal.

The transfer profile is allowed only for source S=32 and integer target
`33 <= L <= 64`. It preserves physical displacement, not a fractional lattice
coordinate. First lift the source kernel to support (33,33), centered at
(16,16). An even-source edge tap at index zero represents the coincident
displacements -16 and +16. Split it equally between these two displacements
on each such axis (quarter weights at a double-edge corner); all other taps
retain displacement `j-S//2`. This lift is linear in C and preserves the sum
over taps. It does not rescale amplitudes by L/S, by volume, or by orbit size.

Next zero-pad that lifted support to (L,L), preserving the offset of each tap
under the circular backend's origin `((L-1)//2,(L-1)//2)`. The zero-displacement
tap must be at that origin for odd AND even L. This convention differs from
the native even-sized origin. Do not wrap the newly padded kernel, split its
edges again, interpolate in frequency space, or refit/fold its weights.
All specified supports fit in the image; shrinking is outside this API.

For either profile, form site embeddings `H[b,x,c]=sum_r A[c,r]*h(phi[b,x])[r]`.
With the profile's kernel and origin, the vector field is the correlation

`v[b,x] = sum_j sum_c K[b,j,c] * H[b,(x+j-origin) mod L,c]`.

Here K may differ per batch row only through lambda. This equation fixes the
sign and phase convention without requiring any particular implementation.

## Differential and transport quantities

`divergence[b]` is the exact Euclidean trace
`sum_x partial v[b,x] / partial phi[b,x]`, at fixed t and lambda. It is NOT
negated, divided by lattice volume, or estimated with random probes.
`dlam_velocity` and `dlam_divergence` are partial derivatives with respect to
the corresponding row's physical lambda, holding the supplied phi and t
fixed. They are not sensitivities along an integrated trajectory, derivatives
with respect to s, or derivatives of model parameters.

Forward transport solves `d phi/dt = v(phi,t,lambda)` and
`d logp/dt = -divergence(phi,t,lambda)` from t=0 to t=1.
Reverse receives a field and density at t=1 and solves the SAME equations
back to t=0. Lambda is constant along each trajectory. Return the transported
input density; never replace it with a Gaussian density or an action. The
input density can be any finite value, and adding a constant to it must add
the same constant to the output. Both directions are judged against absolute
reference outputs, not only a forward/reverse round trip.

The numerical target is this IVP, not a mandated integrator. References use
double precision, the fixed-grid classical RK4 implementation, 100 steps on
[0,1], and separate refinement checks. Exactness of divergence is distinct
from finite-step integration error.

## NPZ protocol

Run `solve.py INPUT.npz OUTPUT.npz` in a fresh process per case. Load with
`allow_pickle=False`. Models are under `$ALE_INPUT_DIR/checkpoints`; if unset,
the starter uses `../input` relative to its own file. Use no private artifacts.
The bundled `input/runtime` is supplied by the runner; the evaluator uses it
when present, otherwise its own Python. NumPy/SciPy and JAX/Haiku/Flax are
available. No network, GPU, or downloaded dependencies are necessary.

All input files contain:

| key | dtype / shape | contract |
|---|---|---|
| model | Unicode scalar | one of the three identifiers above |
| profile | Unicode scalar | native or transfer |
| operation | Unicode scalar | probe, forward, or reverse |
| phi | float64 (B,L,L) | B is 1 or 2; no channel axis |
| logp | float64 (B,) | one density per row; ignored by probe |
| t | float64 scalar | probe time; ignored by transport |
| lam | float64 scalar or (B,) | one shared coupling or row-aligned couplings |

A vector lam does NOT introduce another batch axis, interleave trajectories,
or broadcast every field to every lambda. Fixed models accept only their
listed coupling; conditional values are in [4,6]. Native sizes and transfer
sizes above exhaust the shape contract. All rows are independent.

Required probe outputs:

| key | shape |
|---|---|
| velocity | (B,L,L) |
| divergence | (B,) |
| kernel | (B,L,L,20), the fully contracted, expanded/profile-resized K |
| dlam_velocity | (B,L,L), conditional model only |
| dlam_divergence | (B,), conditional model only |

Repeat K across rows for a shared scalar coupling. For a conditional vector
lam, each row has its own kernel. Probe outputs describe the instantaneous
field; no ODE integration is needed. Required forward/reverse outputs are
`phi` (B,L,L) and `logp` (B,). Extra keys are ignored.

## Evaluation

The default pool and a disjoint challenge pool cover the same public API.
Challenge cases include couplings across the midpoint between neighboring
Gaussian centers, exact interval endpoints, odd/even transfer extents,
displacement-resolved impulses, and separate trajectories. There are no
undisclosed interpolation modes or architecture changes.

Six independent group weights are: vector field .15, divergence .20,
conditional derivative .20 (equal velocity/divergence derivative weights),
geometry/kernel .15, forward .15, reverse .15 (equal field/density weights).
Each group's outputs are averaged equally across applicable cases. A missing,
non-finite, or wrong-shaped required output scores zero for that output.

For an output, let e be the average of RMS relative error and maximum relative
error. Denominators use the reference RMS/maximum, floored at 1e-3 for fields
and kernels and at 1 for density/divergence quantities. For transported logp,
compute the error on `output.logp-input.logp`, so a large prior density cannot
hide an incorrect density change. Numerical quality is `1/(1+e/tau)` with
tau=2e-5 for probes and tau=2e-4 for transport. This is a smooth score, not an
all-or-nothing tolerance; errors considerably below tau are desirable.

Every output quality is multiplied by `1/(1+.03*T/Tref)`, where T is observed
end-to-end subprocess wall time (including imports, checkpoint loading, JIT,
computation and output) and Tref is the premeasured author implementation's
wall time on the same machine. It is strictly decreasing, without a runtime
plateau or a hard accuracy gate. Reported group accuracies also omit this
factor so independent scientific failures remain visible. Processes use CPU
cores 40-43 and at most four compute threads. Timeout is
`max(60 seconds, 3*Tref)`; a killed process scores zero. Runtime scores are
machine-local and should be recalibrated by regenerating references after a
runtime or hardware change. Checkpoint lookup or cached answers for known
cases are not valid implementations.

The starter handles only native fixed checkpoints, using a dense spatial
operator, a full Jacobian trace and a generic adaptive ODE solver. It is a
working but deliberately unscalable starting point, not an inference solution.
