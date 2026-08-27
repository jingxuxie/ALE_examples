# Numerical contract

Use a mostly-minus metric and the causal `+i0` propagator prescription. Every
input number is a real dimensionful squared mass or external squared invariant,
not a mass. An invariant matrix contains `S[i,j]=(p_i-p_j)^2`, is symmetric,
and has zero diagonal. The propagators are `((k+p_i)^2-m_i^2+i0)^nu_i`.

The requested objects are the scalar coefficient representation of covariant
one-loop tensors, also allowing parameter moments after a change of routing.
This formal parameter representation fixes the convention unambiguously:

```
C(r,n,nu;d0,epsilon) =
  (-1)^(sum(nu)+sum(n)+r) / (2^r product_i Gamma(nu_i))
  * exp(gamma_E epsilon) (mu2)^epsilon
  * Gamma(sum(nu)-d0/2-r+epsilon)
  * integral_(x_i>=0,sum x_i=1) product_i x_i^(nu_i+n_i-1)
      [sum_i x_i m_i^2 - sum_(i<j) S_ij x_i x_j - i0]
          ^(d0/2+r-sum(nu)-epsilon) dx .
```

There is no extra simplex factorial. Here `dimension=d0` is an even integer,
the actual dimension is `d0-2 epsilon`, `metric_pairs=r`, `moments=n`, and
`weights=nu`. For ordinary tensor coefficients `n[0]=0`; the general moment
notation also covers parameter insertions. The displayed integral is a
dimensional-regularization definition, **not** a convergent real numerical
integral in every supported regime. Do not redefine it with a nonzero physical
width. Analytic continuation is from the Feynman prescription.

The required Laurent channels are:

```
uv / epsilon_UV + ir2 / epsilon_IR^2 + ir1 / epsilon_IR + finite.
```

These are additive pole origins of a single dimensional regulator, not two
independent integrations. In the `exp(gamma_E epsilon)` convention, gamma-
function factors must be kept to the order that can affect the finite part.
There is no `4 pi` or `c_Gamma` factor to divide out. `mu2` defaults to one.

## Local matching coefficients

Each `directions` entry supplies a linear variation of squared masses and/or
the invariant matrix with a dimensionless variable. Missing entries are zero:

```
masses2(t) = masses2(0) + sum_a t_a directions[a].masses2
S(t)       = S(0)       + sum_a t_a directions[a].invariants.
```

For each requested `orders=[k_0,...,k_A]`, return the coefficient of
`product_a t_a^k_a`, including the Taylor factorials. An empty order has key
`base`; other keys join the orders with commas. Expand each Laurent channel.
These are local Taylor coefficients on the causal sheet, not asymptotic
coefficients at a Landau singularity. None of the requested expansions crosses
a genuine singularity at its center. A zero Gram determinant is not, by itself,
a reason to reject a request.

## Supported release domain

- One through four propagators, positive squared masses except the explicitly
  massless topologies below; even base dimensions 4, 6, or 8.
- Positive integer weights through 3, metric pairs through 2, total moment
  degree through 4, and local coefficients of total degree through 3.
- Massive spacelike configurations, massive timelike configurations above
  normal thresholds, and exactly rank-deficient Gram geometries. No evaluation
  exactly at a Landau singularity is required.
- Massless three-point configurations with exactly one nonzero invariant;
  unit weights, dimension 4, zero metric pairs, nonnegative moment insertions,
  and invariant directions preserving the zero entries. These include double,
  single, and absent infrared poles.
- Massless scalar four-point configurations with zero or one nonzero external
  leg virtuality, two nonzero channel invariants, unit weights and dimension 4.
  There are no Taylor requests for these massless boxes.
- No fully scaleless integrals, complex masses, physical widths, power infrared
  divergences, general two-mass IR boxes, or five-point functions are required.

Hidden release cases exercise these same capabilities in different combinations,
with different routing, scale, tensor weight, causal region, and expansion
directions. They are not a distribution of random labels to be fitted.

## Coupled observables

An observable is a sum of referenced coefficients times a polynomial in epsilon.
`epsilon_polynomial=[a0,a1,a2]` means `a0+a1 epsilon+a2 epsilon^2`.
Multiply before dropping terms beyond the finite part. For example the physical
metric trace uses `d=4-2 epsilon`, not the integer four. The two regulators in
the output are bookkeeping labels: epsilon multiplying either single pole
contributes a finite term. `expected_zero` is a mathematical diagnostic, not a
license to set the underlying integrals to zero. All constituent coefficients
are independently evaluated. A positive `normalization` only scales a reported
diagnostic residual; it never changes an integral.
