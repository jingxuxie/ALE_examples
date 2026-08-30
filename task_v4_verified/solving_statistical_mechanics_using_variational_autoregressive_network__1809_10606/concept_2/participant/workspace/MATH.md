# Exact finite-space definitions and verification

All logarithms are natural. There are 16 physical spins in {-1,+1}. For each
of the 32 undirected edges, use the supplied coupling exactly once:

    E(s) = -sum_edges J_uv s_u s_v
    U(s) = beta E(s)
    log Z = log sum_s exp(-U(s))
    log p(s) = -U(s) - log Z.

A plaquette is frustrated precisely when the product of its four bond signs is
-1. Beta is already included in U; do not divide reported reward quantities by
beta or by system size except where the specification explicitly says so.

Write t_i = s_order[i], and l_i = sum_{j<i} W_ij t_j. The witness distribution is

    log q(s) = sum_i log sigmoid(t_i l_i).

The first spin is exactly uniform. The row bound implies every binary
conditional probability is in [0.0001,0.9999], and q(s) >= 0.5*(0.0001)^15.
No probability is clipped, discarded, or floored during evaluation. The
zero-bias parameterization gives q(s)=q(-s), for any order.

Define R(s)=U(s)+log q(s), and mu_R=sum_s q(s) R(s). Exhaustive sums give:

    entropy = -sum_s q(s) log q(s)
    reverse_kl = sum_s q(s) (log q(s) - log p(s))
    reward_variance = sum_s q(s) (R(s)-mu_R)^2
    energy_error_per_spin = abs(sum_s (q(s)-p(s))*U(s)) / 16.

For each free lower-triangular coordinate, the score is

    z_ij(s) = ((t_i+1)/2 - sigmoid(l_i)) * t_j, j<i.
    gradient_ij = sum_s q(s) (R(s)-mu_R) z_ij(s).

`gradient_infinity` is the maximum absolute value among these 120 entries. This
is the ambient-coordinate derivative of KL (equivalently beta times the free
energy derivative), not a projected gradient and not a sample estimate. Small
gradient does not certify a local minimum. Diagonal and upper entries are zero.

For the submitted physical pattern xi and radius r,

    A = {s: min(Hamming(s,xi), Hamming(s,-xi)) <= r}.

`target_sector_mass=sum_A p(s)` and `proposal_sector_mass=sum_A q(s)`. These
are masses of the union, not separate requirements for the two balls.

The seven metric gates in `input/spec.json` are simultaneous. Lower bounds
accept measured >= target - 1e-10; upper bounds accept measured <= target +
1e-10. Structural bounds have no slack. Exhaustive evaluation uses float64,
stable log-sum-exp and centered variance; it is not symbolic rational arithmetic
or a formally interval-certified computation. The evaluator also checks
normalization and global spin-flip symmetry without renormalizing q.

For each lower-bound gate its score is clip(measured/target,0,1). For each
upper-bound gate it is min(1,target/measured), with score 1 for measured=0.
`core_score`, `worst_score`, and `worst_family_score` are the minimum of the
seven scores. A structurally invalid submission scores zero. `passed` is true
only when every structural and metric check passes and evaluation completes
within its resource limits; a displayed rounded score of 1 is not a substitute.

The report lists all metrics, gate scores, failing gates, the worst gate,
validation data, CPU/wall/RSS resource measurements, `valid`, `evaluator_valid`,
`passed`, and `reason`. Resources are evaluator limits, not a promise about
participant hardware. The exact finite-space zero-variance identity is not being
challenged: with full support, variance exactly zero implies q=p.
