# Public certificate, not secret sampling

The evaluator independently assembles Fourier hopping matrices `T_R` with
`H(k)=sum_R T_R exp(i k.R)`. It does not import the participant utilities and it
never executes submitted code. It evaluates complete 2-by-2 matrices with
`numpy.linalg.eigvalsh`. Standard evaluation uses a periodic 320-by-320 momentum
mesh, including -pi, and five equally spaced samples in each of u and v, including
both endpoints. These meshes are fixed, not selected by the witness.

For central manufacturing variables u,v, set
`Lx=sum_R |Rx| ||T_R|| + 0.06`, likewise Ly; set
`Qx=sum_R Rx^2 ||T_R|| + 0.06`, likewise Qy. Norms are operator norms.
For the four coordinates `(kx,ky,u,v)`, set
`L=(Lx,Ly,1,sqrt(2))`, `Q=(Qx,Qy,0,0)` and grid spacings
`h=(2*pi/320,2*pi/320,0.10/4,0.12/4)`.

1. A nearest-grid-point Weyl bound gives the uniform preliminary gap
   `g_star=min_grid(E1-E0)-sum_j L_j h_j`. If this is not positive, certification
   fails rather than asserting continuum isolation.
2. On this gapped domain each eigenvalue has
   `|partial_j^2 E| <= Q_j + 2 L_j^2/g_star`.
   Tensor-product linear interpolation therefore has uniform eigenvalue error
   `epsilon=sum_j (Q_j+2 L_j^2/g_star) h_j^2/8`.
3. The independent relative coefficient box changes the Hamiltonian norm by at
   most `eta=0.004 [sqrt(2) sum|a| + sum_pq w_pq (|b|+|c|)]`, where w=1 when p=q
   and w=2 otherwise. This bound covers every coefficient combination, including
   channels that nominally vanish.
4. For every sampled u,v, compute momentum-mesh bandwidth, direct gap and
   indirect gap. Define `W_cert=max_scenarios W_grid+2(epsilon+eta)` and each
   `g_cert=min_scenarios g_grid-2(epsilon+eta)`.

The last step uses the SAME uncertainty-interpolation weights for every momentum:
the width of the interpolated band is at most the weighted widths of the corner
bands. It does not incorrectly subtract energy extrema from different samples of
u,v. Consequently the certificate controls the bandwidth of each manufactured
device, rather than a pooled linewidth across devices.

Topology is cross-checked on a separate 128-by-128 periodic mesh: the lower-band
FHS link invariant must agree with minus the oriented solid-angle degree of d/|d|.
At each elementary cell the full continuum vector and its piecewise-linear
interpolant remain in a ball about a corner vector of radius at most
`(Lx_nominal+Ly_nominal)*2*pi/128`. Requiring this radius to be less than the
smallest sampled |d| certifies a nonvanishing straight homotopy to that interpolant.
Thus an integer returned on a coarse grid alone is NOT the continuum certificate.
Links must be nonsingular, plaquette phases must be less than pi/2 in magnitude,
and both independent integer residuals must be below 2e-8. A second shifted mesh
and randomized eigenvector phases audit this calculation.

The published implementation uses float64, conservative norm inflation of 1e-12
plus 1e-14, and energy padding `2e-10*(1+sum_R ||T_R||)`. This is an analytic
continuum bound with numerical safety margins, not a formal interval-arithmetic
proof. The evaluation report exposes all constants, errors and margins. Separate
tests compare matrix spectra with closed two-level eigenvalues, shifted/refined
grids, direct spherical degree, and adversarial manufacturing samples.
