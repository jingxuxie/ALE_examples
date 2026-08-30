# Numerical formulation and development notes

Let `n=d+1`, `V_s=-log(mu_s)`, and let `P(x)` be the node polynomial.
Define positive barycentric magnitudes

    c_si = 1 / (mu_s(t_i) product_{j != i} |t_i-t_j|).

Away from the nodes, the weighted Lebesgue function has the representation

    L_s(x) = mu_s(x) |P(x)| sum_i c_si / |x-t_i|.

The implementation stores logarithmic coefficients, subtracts their largest
value within each scenario, and evaluates the resulting positive sum. This
avoids overflow from reciprocal weights or products of many node differences.
Using `log1p(x/p)` simply normalizes each prefactor to one at the origin;
scenario-dependent multiplicative constants cancel from the objective.

## Peak derivatives

Write `r_i=1/(x-t_i)` and let `rho_i` be the normalized positive contributions
`c_si/|x-t_i|`. Then

    (log L_s)' = sum_i r_i - sum_i rho_i r_i - V_s'(x),

    (log L_s)'' = -sum_i r_i^2 + 2 sum_i rho_i r_i^2
                 - (sum_i rho_i r_i)^2 + sum_p 1/(x+p)^2,

where `V_s'(x)=a_s+sum_p 1/(x+p)`. These formulas polish golden-section peak
searches with safeguarded Newton steps. Searches use a coordinate proportional
to `log(x+offset_s)`, with `offset_s=1/V_s'(0)`, rather than a uniform physical
coordinate. This distinction matters when the entire effective support is near
a very small repeated pole.

## Gap derivatives

Changing gap `g_k` translates precisely the nodes with indices `i>=k`.
The derivative of the log Lebesgue function with respect to `log(g_k)` is

    g_k [sum_{j>=k} (rho_j V_s'(t_j) - (1-rho_j)/(x-t_j))
         - sum_{i<k<=j} (rho_i+rho_j)/(t_j-t_i)].

The second sum involves only pairs crossing the gap. Computing it directly
avoids subtracting large internal forces within a tightly clustered set of
nodes. For a free first-node displacement, `k=0` and the crossing sum is empty.
At stationary interior peaks, the envelope derivative is this same derivative;
the derivative of the maximizing location does not contribute. Known nodal
maxima have value one and zero parameter derivative.

## Exterior intervals

For `0<=x<t_0`, each absolute cardinal polynomial is a product of positive,
decreasing factors, and the prefactor is decreasing. Thus the maximum on this
interval occurs exactly at zero. This value is an explicit constraint whenever
the first node is free.

After scaling by the smallest damping, all damping coefficients are at least
one. For `x>t_d`, the logarithmic derivative of each weighted absolute cardinal
term is bounded above by

    d/(x-t_d) - a_s.

Consequently all terms decrease beyond `t_d+d+1`, providing a finite endpoint
for the exterior peak search without truncating a potentially increasing tail.

## Optimization and experiments

The outer problem minimizes an epigraph variable bounding every scenario's
logarithmic interval peak. Positive gaps are parameterized logarithmically.
Weighted equilibrium mixtures initialize the search but are not the objective.
A boundary-anchored solve supplies a reliable candidate; a subsequent solve
also permits the first node to move right and includes the value at zero.
Only improved representable candidates replace the incumbent.

Early uniform-coordinate tail searches missed narrow maxima in low-degree,
many-pole tests. Logarithmic coordinates corrected these failures. Independent
peak searches scan both linear and logarithmic meshes before local polishing.
Additional checks evaluate selected peaks with 90-digit arithmetic and compare
analytic gradients with central finite differences.

Longer SLSQP runs mostly produced negligible gains at a substantial CPU cost.
Freeing the first node produced genuine gains for uncertain pole counts and
clusters, so that refinement is retained within the same CPU guard.

The local outer optimization does not prove global optimality, and the numerical
peak searches are not formal interval-arithmetic certificates. The submitted
program does not supply or rely on claimed scores or certificates; the external
evaluator remains responsible for independently enclosing its objective.
