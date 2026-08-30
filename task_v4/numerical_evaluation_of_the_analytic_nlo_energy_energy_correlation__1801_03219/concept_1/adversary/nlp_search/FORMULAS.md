# Prospective endpoint residual: exact LP conversion

This sidecar is not a new generation or an original-contract counterexample.
Only files in this private directory are written. The deployed champion,
participant, evaluator and original scientific response remain unchanged.

Source: arXiv:1801.03219v2, Eqs. (8), (11), (12), inspected 28 August 2026.
Write the conventional CF^2, CF*CA and CF*Nf*Tf coefficient functions as
H_F, H_A and H_f. In the supplied leading/subleading/fermion basis:

```
B_lc = H_F + 2 H_A,   B_nlc = H_A,   B_nf = H_f.
```

Let L=log(epsilon), where epsilon=z on the left and epsilon=1-z on the right.
The exact leading-power subtraction is B_LP=P(L)/epsilon.

## Collinear LP polynomials

```
P_lc(L)  = (-481/480)L + 359281/43200 - (7/12)zeta(2)
P_nlc(L) = (-107/120)L - (25/12)zeta(2) + zeta(3)/2 + 17683/2700
P_nf(L)  = (53/240)L - 4913/3600.
```

## Backward LP polynomials

```
P_lc(L)  = L^3/2 + (49/12)L^2 + (2*zeta(2)+59/18)L
           + (17/2)zeta(2) + 2*zeta(3) - 25/16
P_nlc(L) = (11/12)L^2 + (zeta(2)/2-35/72)L
           + (11/4)zeta(2) + (3/2)zeta(3) - 35/16
P_nf(L)  = -L^2/3 + L/18 + 3/4 - zeta(2).
```

## Correct residual chart and conditioning

For t=log(z/(1-z)), q=z(1-z), and the deployed F=q*B:

```
F_LP,left  = (1-z) P_left(log z)
F_LP,right = z P_right(log(1-z))
G = (F-F_LP)/q = B-B_LP.
G' = (F'-F_LP')/q - (1-2z)*G.
```

The factors z and 1-z cannot be discarded: doing so changes the NLP term.
Likewise replacing log(epsilon) by -abs(t) changes NLP coefficients. The audit
uses the exact logistic geometry, high-precision logarithms and the exact LP
functions, and evaluates both logistic tails separately in binary64.

For a density approximation error delta_F, the representation-only residual
error is exactly delta_G=delta_F/q, and its derivative error is
`delta_G'=[delta_F'-(1-2z)delta_F]/q`. This is the relevant downstream
conditioning, not evidence that the original density contract was violated.

`audit.py` also derives the full NLP logarithmic polynomials of Eqs. (11)/(12)
using the same color transformation, then checks that `B-B_LP-NLP` tends to
zero at t=+/-30,40,50,60 using independent 200/280-dps source evaluations.
Same-domain residuals use 160/220 dps and derivative stencils use two steps.

For diagnostic scaling only, G grows linearly in log(z) on the left; on the
right its leading degree is three for lc/nlc and two for nf. This sidecar
reports raw G/G' errors and mixed relative errors, without inventing or
freezing a new tolerance.
