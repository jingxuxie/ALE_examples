# One-loop coefficient release assessment

## Decision

**Reject the inherited release; release the replacement with explicit numerical
convergence diagnostics, not a blanket uniform-accuracy guarantee.** Every public
production coefficient and every final synthetic production stress case completes
without a refinement warning. Both supplied calibration tests and 11 additional
test methods pass: 13 methods, including 117 quantitative comparisons. The final
public campaign takes about 0.5 seconds inside the service, below one second
including startup on this machine. Its 36 coefficient rows are in `results.csv`.

Agreement with the distinct `direct` profile is at most `6.48e-15` on the public
campaign and `4.87e-13` on the published stress campaign. These are **observed
cross-calculation disagreements, not exact error bounds**. Independent analytic
checks, described below, are necessary evidence beyond that agreement. In
particular, the two IR profiles share formulas, so their zero disagreement alone
does not validate IR physics.

## Controlled baseline and diagnosis

`baseline/` contains the unmodified source and profiles, its separately executable
launcher, all three measured campaigns, CSVs, PNG/CSV pairs, `diagnosis.json`, and
`calibration.txt`. No participant source was edited. The baseline was run and
inspected before replacing the numerical stages. Scientific imports were checked
first; NumPy/SciPy/SymPy/mpmath were available, Matplotlib was not. The supplied
dependency-free PNG writer is used instead (`environment.json`).

The baseline failed both exact checks: the tadpole UV residue differed by
`1.94e-4`, and the finite equal-mass box acquired a spurious pole of `1.19e-5`.
The dimensionally contracted trace residual was `1.1176037931`, despite an
advertised internal error of `9e-6`. Increasing the inherited quadrature order
made the physical scalar box finite real part move approximately
`20.05 -> 99.62 -> 556.94`; that is not convergence.

Distinct faults were identified rather than treating all disagreement as noise:

1. Mass sorting permuted weights but not moments or directions, changing tensor
   and local quantities. The result cache omitted weights, moments, dimension,
   metric pairs and numerical settings. Consequently unrelated coefficients
   became identical, sometimes at zero reported additional work.
2. The denominator used `+i regulator`, opposite to the parameter-space `-i0`
   prescription. Real-axis quadrature with a shrinking width also cannot
   integrate physical-cut distributions, especially their higher derivatives.
3. Three positive-epsilon samples were fitted to a truncated Laurent model.
   Omitted positive powers contaminated finite terms and manufactured poles.
   Endpoint-divergent massless integrals are not ordinary convergent quadratures
   at those positive epsilon values; changing epsilon or node count cannot repair
   that scientific error.
4. Finite differences of contaminated sampled values amplified local-coefficient
   errors through cubic and mixed stencils. Uniform scale changes did not remove
   these errors. The existing epsilon-polynomial observable assembly was already
   algebraically correct; corrupt constituents, rather than a license to force
   the trace to zero, were the root issue.

`baseline_comparison.csv` measures before/after against the same refined
comparison. The largest inherited relative disagreement by family is 5.44
(weighted), 10981 (physical cut), 2.00 (UV), 174 (triangle), 17.5 (box), and 0.0420
(local matching). These large errors cannot be explained by modest node-count
uncertainty. The repaired trace residual is `3.27e-16`.

## Mathematical and numerical replacement

Write `a=sum(nu)-d0/2-r` and `K=sum(k)`. Differentiating the formal parameter
integral, including Taylor factorials, gives the local integrand

```
prefactor * (-1)^K / product(k!) * product(delta_a Q ^ k_a)
          * Gamma(a+K+epsilon) * exp(gamma_E epsilon) * (mu2)^epsilon
          * Q^(-a-K-epsilon).
```

This identity works when the Gram determinant vanishes and automatically handles
the disappearance of UV poles after enough derivatives. For `b=a+K>0`, only
`Gamma(b) Q^-b` contributes at finite order. For `b=-p<=0`, the UV integrand is
`(-1)^p Q^p/p!` and its finite partner is that residue times
`H_p + log(mu2) - log(Q)`. The gamma-function convention and metric-pair sign
are therefore retained algebraically, without epsilon fitting or subtraction of
nearby samples. All requested jets reuse the same quadrature nodes.

Masses, invariants, directions and `mu2` are normalized by a common squared-mass
scale; the final factor is `scale^-a`. Smooth massive requests use real Gaussian
simplex integration. A quadratic-program minimum is found by enumerating
stationary points on all simplex faces, without inverting a Gram matrix.

For cuts, with normalized `g=m-Sy`, use
`z_i=y_i-i lambda y_i(g_i-sum(y*g))`, including the exact complex tangent
Jacobian. This preserves every simplex face and `sum(z)=1`. Since `Q` is
quadratic,

```
Im Q(z) = -lambda * (sum(y*g*g) - sum(y*g)^2) <= 0.
```

Thus this is a causal contour homotopy, not a finite physical width. Integer
parameter moments and weights are evaluated on the deformed contour. Negative
signed zero selects the lower lip if the imaginary part vanishes numerically.
Gaussian refinement is followed, when necessary, by cell subdivision. Mixed
low/high tensor rules estimate each axis's unresolved contribution; production
splits the most important direction rather than cycling axes.

Massless triangles are evaluated from the exact Dirichlet gamma product
`Gamma(1+eps) Gamma(n_A-eps) Gamma(n_B+1) Gamma(n_C-eps) /
Gamma(sum(n)+1-2eps)`, where `(A,C)` is the nonzero invariant. Its pole order
is the number of zero endpoint moments. Harmonic-number expansion keeps terms
through finite order, including local invariant derivatives.

Zero/one-mass boxes use the causal log/dilog formula, including
`exp(gamma_E eps) Gamma(1+eps) Gamma(1-eps)^2/Gamma(1-2eps)
=1-pi^2 eps^2/12+...`. This otherwise easy-to-miss factor affects finite terms
multiplying the double pole. Channel pairings are discovered from the invariant
matrix, not fixed routing or IDs. Dilog lips follow the difference of causal
channel logarithms. UV, double-IR and single-IR labels remain distinct. Epsilon
polynomials multiply these channels before finite-order truncation.

## Validation and genuine design ablations

`independent_checks.csv` records every numerical assertion with its tolerance.
Besides the two supplied tests, the checks include:

- 36 equal-mass Dirichlet normalizations over one to four propagators, dimensions
  4/6/8, metric pairs 0/1/2 and nontrivial weights/moments (worst `1.88e-15`).
- Routing permutations, moment partition, dimension shift, weighted mass
  derivatives, mixed Taylor factorials, UV jets and pole disappearance.
- Scale covariance, renormalization-scale Laurent mixing, and explicit
  epsilon-polynomial IR subtraction/assembly.
- Independent real-axis, root-split logarithmic integration for above-threshold
  scalar/tensor/metric bubbles, including their cut imaginary parts
  (worst `1.34e-14`).
- 55-digit Cauchy extraction of triangle gamma-function Laurent coefficients,
  covering absent, single and double IR poles and both signs of the invariant.
- An independent projective-parameter endpoint subtraction integral for box
  finite parts, rather than comparing the box formula to itself (worst
  `1.89e-16`), and simultaneous causal phase continuation of both box types.

`ablation.csv` and `scaling.csv` retain the supplied columns and configuration
hashes. The comparison metric is the maximum absolute real/imaginary component
difference across the four channels divided by the largest reference component,
then maximized over coefficient rows when reported for a case or campaign.
Public worst disagreement versus the distinct-contour `direct` run is:

| Configuration | Total node/formula work | Worst disagreement |
|---|---:|---:|
| `order_8` | 4,077 | 1.79e-3 |
| `order_12` | 15,749 | 1.15e-4 |
| `order_20` | 84,789 | 3.49e-7 |
| `order_32` | 326,321 | 1.56e-10 |
| `order_52` | 1,311,121 | 2.31e-14 |
| `order_80` | 4,568,661 | 2.13e-14 |
| `fixed` | 38,213 | 3.49e-7 |
| `production` | 654,601 | 6.48e-15 |
| `direct` | 766,501 | comparison, not exact truth |

The plateau at high order indicates floating-point sensitivity, not indefinitely
increasing accuracy. Production spends nodes where needed rather than imposing
the expensive high-order rule universally. Timings are measured, not modeled;
see the CSVs and `summary.json` for this machine's startup and per-family times.

The first attempted contour-only policy failed sufficiently close to threshold.
This caused an actual revise/rerun loop, not merely a larger reported error bar.
`stress_requests.json`, `stress_ablation.csv`, and `stress_scaling.csv` reproduce
the consequential fallback ablations with four executable configurations:

| Stress case | Tensor-only disagreement | Cyclic subdivision | Production directional |
|---|---:|---:|---:|
| s=4.05, unit internal masses | 6.95e-8 | 1.80e-15 | 3.86e-16 |
| s=4.0005, unit internal masses | 5.23e-3 | 1.50e-15, warning | 9.97e-16 |
| masses2=0.001,1,10,100 | 0.926 | 3.85e-8, warning | 9.29e-14 |
| four weights of 3, moments and cubic jets | 4.87e-13 | 4.87e-13 | 4.87e-13 |

All entries compare to `direct`, whose contour strength, rules and tolerance
differ. On the hierarchy, directional splitting reduces work from 5,004,992 to
1,249,856 while removing the cyclic scheme's unresolved error. The full four-case
production stress campaign takes roughly 7-8 seconds. A separately measured run
uses 302,944 KiB peak RSS, 98% of one CPU, no swap, and 8.28 seconds wall time
(`resource_usage.txt`), comfortably below the stated memory and time budgets for
these measured cases. This is not a measurement of an unseen campaign.

`claims.json` ties seven quantitative comparisons to exact table/profile/case
selections; `workspace/check_claims.py` checks them. `figures/primary_result.png`
plots before/after cross-calculation disagreement versus work.
`figures/robustness_or_scaling.png` plots public work versus measured time.
`figures/adaptive_stress.png` adds the fallback comparison. Each has its complete
source CSV alongside it. Zero profile disagreement is plotted at the helper's
floor and must not be interpreted as infinite precision.

## Limitations and operational contract

- No finite experiment establishes uniform eight-digit accuracy arbitrarily
  close to every Landau surface or for unbounded mass hierarchies. Subdivision is
  bounded; exhausted requests return their actual estimate with
  `converged=false` and `UNCONVERGED`, never zero or a concealed exception.
- Internal estimates are heuristics. The maximum-weight stress discrepancy is
  several times production's internal estimate, although still below `5e-13`.
  Cancellation-dominated coefficients can lose relative digits; changing the
  contour and checking identities remains important for critical applications.
- The IR implementation is restricted to precisely the documented massless
  triangle and zero/one-mass box regimes. Mixed massive/massless topologies,
  scaleless integrals, general two-mass IR boxes, physical widths, and expansion
  at a genuine singularity are not silently approximated.
- `direct` shares the analytic Laurent/Taylor and IR stages with production.
  Independent identities and integral checks reduce, but cannot eliminate,
  common-mode risk. The public campaign is not a complete oracle, and no hidden
  reference values were accessed.

The portable prediction entry point is `run.sh`; `reproduce.sh` regenerates the
published evidence. Configuration and diagnostic semantics are documented in
`workspace/README.md`. No service result depends on request IDs or observables
being marked `expected_zero`.
