# Predictor methods and release policy

## Conventions and response

All states and channels use column-major vectorization. Set
`L(H) = -i (I ⊗ H - Hᵀ ⊗ I)` and absorb the complete mixing matrix,
standard deviations and segment sensitivities into Hermitian operators
`B_m(t) = sigma_m sum_a sensitivity_a(t) mixing_am operators_a`.
Only scalar identity components, which generate no channel action, are removed.
No computational-subspace projection is made.

For static noise use `r_m=0`; for OU/broadband use the supplied rates; for
telegraph covariance use twice the supplied switching rates. With
`A_m=L(B_m)`, propagate the following piecewise-constant augmented system:

```
P'   = L(H) P                         P(0) = I
Y_m' = (L(H) - r_m I) Y_m + A_m P     Y_m(0) = 0
Z'   = L(H) Z + sum_m A_m Y_m         Z(0) = 0
k2   = P(T)† Z(T)
```

This is the ordered double covariance integral, including its coherent part,
not a fitted rate or a symmetrized covariance integral. Sparse exponential
actions propagate complete control segments. Sensitivity changes occur exactly
at their specified boundaries. Bath restarts erase `Y_m`, not `Z` or the ideal
history. White noise instead uses the Fréchet derivative of the segment
exponential in direction `D = sum_m A_m²/2`.

## Finite-noise channels

- **Static Gaussian:** tensor Gauss-Hermite quadrature of exact piecewise unitary
  products. A latent draw persists throughout the complete record. Gaussian
  latent modes with identical rates may be orthogonally rotated to remove
  redundant covariance directions; telegraph modes must not be rotated this way.
  Numerical Gram directions below `1e-13` of its largest eigenvalue are pruned.
  Up to three active static modes use quadrature; higher rank uses the Hermite
  hierarchy. Quadrature orders increase until the relative channel change is
  below `2e-6` (selected) or `2e-8` (refined).
- **OU/broadband Gaussian:** normalized Hermite stochastic-Liouville hierarchy.
  An index vector `n` has damping `sum_m n_m r_m`; adjacent indices couple via
  `sqrt(n_m+1) A_m`. The stationary initial condition has only the zero mode.
  The total-degree cutoff increases and the full complex channel, not just
  its trace, is checked for convergence. Degrees are chosen from arrays and
  the noise law, never a case identifier.
- **Telegraph:** Walsh moments of independent stationary sign variables,
  equivalently the conditional classical Markov master equation. Each bit is
  either zero or one, flips couple with coefficient one, and damping is twice
  the physical switching rate. Small baths retain every sign configuration
  and are exact up to exponential-action roundoff. Larger baths use tested
  total-degree truncations and disclose whether convergence was reached.
- **White:** each segment is exactly `exp(dt [L(H)+D])`. The factor one half is
  fixed by the stated Stratonovich covariance. Segment products preserve
  noncommuting dissipative time ordering. Bath restarts have no effect.

For Hermite/Walsh dynamics the zero bath mode is represented as the deviation
from the ideal channel, with the ideal channel carried as a separate source.
This prevents repeated propagation of an order-one ideal component from
dominating the error of an order-1e-6 weak-noise channel.

`no_memory` uses the same physical model but independently reinitializes all
nonzero bath moments at each supplied block boundary. Static quadrature instead
averages each block and composes the block channels. `selected` ignores block
boundaries as bath operations. `refined` uses higher quadrature/hierarchy settings
and halves exponential steps for the response and exact small-bath methods.
For the weak branch it changes the physical approximation from second-cumulant
closure to a fourth-order-exact bath propagation, rather than relabeling a run.

## Certified weak-bath shortcut

Define the scalar envelope using the spectral diameter of each `B_m`:

```
b = sum_m integral_{0<s<t<T} diameter(B_m(t)) diameter(B_m(s))
                                  exp(-r_m (t-s)) ds dt
R2(b) = exp(b) - 1 - b
```

The envelope is integrated analytically over each constant segment, carrying
its memory between segments. For Gaussian noise, Wick's theorem and the
operator-norm triangle inequality give
`||Phi - Phi0(I+k2)||F <= d R2(b)`. The Gaussian envelope also bounds the even
ordered moments of independent symmetric telegraph processes; its covariance
alone is nevertheless insufficient to determine their actual higher moments.

Because `||k2||op <= b`, the second-cumulant exponential has absolute error at
most `2 d R2(b)`. The denominator lower bound is
`||k2||F - d R2(b)`; small denominators are treated conservatively relative to
the contract's error floor. The selected shortcut is allowed only when this
relative bound is below `2e-4`. This criterion includes the complete sequence
and noise memory, not just the size of one gate's infidelity.

A total-degree-two Hermite/Walsh hierarchy agrees with the exact Dyson series
through fourth order. Omitted paths first reach degree three. Their positive
scalar bath weights are a subset of the Gaussian Wick bound, giving the tail
`d [exp(b)-1-b-b²/2]`. A stable power series evaluates that tail for small `b`.
The refined weak calculation uses this certificate, with relative truncation
bound below `2e-9`. These analytic bounds concern the represented stochastic
model and truncation, not floating-point errors or numerical rank pruning.

## Resource and accuracy disclosures

The entry point sets BLAS/OpenMP to one thread and imports only NumPy/SciPy
for selected propagation. Legacy-only packages are loaded lazily. The preserved
baseline retains its original positive-frequency mesh, regularized static PSD,
discarded frequency shifts and independent gate forecasts.

Quadrature is batched in at most 2,048 unitaries, with at most 70,000 tensor
nodes. General bath propagation caps the basis at 3,000 bath states and
6,000,000 complex state entries. It stops initiating convergence passes after
55 seconds; an 85-second deadline is checked inside channel propagation.
If a pass cannot finish, the last *completed* channel is retained. If none
finished, the result is explicitly labeled a budget-limited cumulant fallback.
The independently computed response is still returned. No segment is silently
discarded and no bath memory is silently changed to satisfy the budget.

These are practical guards, not a hard preemption mechanism: the response
calculation and a currently executing matrix-exponential action can exceed a
deadline on extreme input. Unconverged or fallback channels are not certified.
The public measurements, including fresh-process wall time, establish the
tested resource envelope; they do not prove all future inputs fit it.

Adjacent quadrature/hierarchy agreement is empirical. Analytic commuting-noise
solutions, independent quadrature versus Hermite calculations, finite-difference
response tests, representation checks, lab checks and trajectory diagnostics
provide complementary evidence. CP/TP/unitality are sanity checks, not accuracy
certificates. Tiny negative Choi eigenvalues at roundoff are retained rather
than projecting the channel and concealing errors.
