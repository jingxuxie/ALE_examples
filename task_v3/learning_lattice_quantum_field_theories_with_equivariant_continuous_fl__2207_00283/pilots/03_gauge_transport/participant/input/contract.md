# Interface and mathematical contract

Every input is an NPZ, loaded with `allow_pickle=False`. Arrays are float64
or complex128. `links` has shape `(Lx,Ly,2,N,N)`, a periodic 2D gauge field;
`N` is 1, 2, or 3. The groups are U(1), SU(2), and SU(3), respectively.
Sizes range from 4 to 16 sites along each axis, including rectangles.
`generators` has shape `(G,N,N)` and supplies the exact skew-Hermitian
Lie basis defining the metric; do not renormalize it. `weights` has shape
`(3,3,4)`. The scalar potential V(U,w,t) is defined by the supplied
`workspace/potential.py`; its oriented paths and normalizations are the
specification. All matrix products use the displayed order.

For each link e and generator a, define
`D[e,a] f(U) = d/ds f(U with U[e] replaced by exp(s*T[a]) @ U[e]) at s=0`.
The vector field in left-trivialized coordinates is
`A[e] = sum_a D[e,a] V * T[a]`, and its Haar divergence is
`div A = sum_(e,a) D[e,a] D[e,a] V`.
The trajectory solves `dU[e]/dt=A[e] @ U[e]` and
`dlogq/dt = -div A`, starting at `links` and logq=0 at `t0`, ending at
`t1`. Either time direction is supported; endpoints lie in [-0.5,1.5]
and durations have magnitude at most 0.6. Time-dependent weights remain
functions of physical t, including on reverse trajectories.

`probe` is a complex array shaped like `links`, and `density_weight` is
a real scalar. The terminal scalar objective is
`J = real(sum(conj(probe)*U(t1))) + density_weight*logq(t1)`.

Write six arrays:
- `vector`: A at the input field and time t0, same shape as `links`.
- `divergence`: scalar div A at that point.
- `state`: U(t1), same shape as `links`.
- `log_density`: scalar logq(t1), relative to product Haar measure.
- `weight_gradient`: dJ/dweights, shape `(3,3,4)`.
- `initial_gradient`: sum_a (D[e,a] J)*T[a] for every initial link e,
  shaped like `links`; the derivative moves only the initial field,
  keeping probe, weights and time endpoints fixed.

Outputs describe the continuous trajectory, not a mandated discretization.
Use double precision and aim for relative errors below 1e-5. Accuracy in
each output, each group family, and forward/reverse transport is scored
separately. Exact zero divergences in some configurations do not exempt
other branches. Full-size cases are integral to the task. Each case receives
240 seconds and eight CPU cores; startup/compilation counts. Numerical
quality decreases continuously with error relative to the identity baseline;
timeouts receive no credit for the missing outputs. Evaluation uses fresh
processes. The two supplied inputs are unlabeled smoke cases, not training data.
