# Complete synthetic generative law

This is an exactly solvable physical *forward model*, not an assertion that
arbitrary device noise is globally depolarizing. Its identification problem is
unknown, sparse and nonlinear in the observed shot likelihood. The seed paper
is Proctor et al., *Scalable randomized benchmarking of quantum computers using
mirror circuits*, arXiv:2112.09853, especially the even-depth mirror protocol,
depolarizing-channel product law, and entanglement-infidelity scaling. This
task isolates adaptive crosstalk identification rather than circuit compilation.
`model.py` is the executable specification; there are no undisclosed families,
parameter transformations, or extra noise sources.

## Graph, rates, and observations

There are 4×4, 4×5 or 5×5 rectangular nearest-neighbor grids: 16, 20 or 25
qubits and 24, 31 or 40 native edges. Vertices are row-major; undirected edges
are lexicographically sorted endpoint pairs. A native layer applies Clifford
two-qubit gates on a matching and single-qubit gates elsewhere. All fixed
single-qubit/background effects are represented by the layer intercept.

Write `x_e=1` when native edge `e` is active, else zero. Candidate interactions
are **every unordered pair of vertex-disjoint native edges**, including distant
pairs. Let

```
lambda(M) = idle + sum_e base_e*x_e + sum_{e<f} cross_ef*x_e*x_f
p(M) = exp(-lambda(M))
rate(M) = (1-4**(-n)) * (1-p(M))
```

Every layer's error channel is exactly
`D_p(rho)=p*rho+(1-p)*I/(2**n)`. Rates are nonnegative and `0<p<=1`, so this is
a completely positive trace-preserving channel for every legal matching.
Forward and inverse layers have the same matching and the same channel.
After an even number `depth` of these layers, the ideal mirrored output is a
known bitstring. A further depolarizing SPAM channel has contrast `A(M,t)`.
The probabilities of its exact target and of each other bitstring are

```
z = A(M,t) * exp(-depth*lambda(M))
P(target) = z + (1-z)/2**n
P(each other string) = (1-z)/2**n
successes ~ Binomial(shots, P(target))
```

This is a normalized distribution on all `2**n` strings, not a linearized
survival approximation. Only target success/failure counts are exposed, which
are sufficient for this distribution. There is no Gaussian shot approximation,
clipping of an invalid physical probability, or circuit-to-circuit overdispersion.
`rate` is entanglement infidelity, not `(1-2**(-n))*(1-p)` average gate infidelity.
Depth-zero matching labels specify the same SPAM context even though no
benchmark layers execute. The context is a control/readout setting retained at
depth zero; it does not contribute additional gate noise.

## Parameter draws

Draws use independent NumPy PCG64 generators from three `SeedSequence(seed)`
children for parameters, fixed targets, and shots, respectively. Private seeds
are independent 128-bit random integers. No private seed or coefficient is in
the participant assets. Unless coupled explicitly below, draws are independent.
Uniform endpoint conventions are NumPy's half-open convention.

All families have `idle ~ Uniform(0.001,0.004)`. The support size is
`round(0.30*number_of_edges) + J`, with `J` uniform on `{-1,0,1,2}`.
Choose that many candidate pairs **without replacement**, weighted as below.
All unsupported coefficients are exactly zero. Distance between edges is the
minimum Manhattan distance between their endpoints; their center is the mean
coordinate of their two endpoints.

| Disclosed family ID | Base coefficients | Support weights and nonzero crosstalk |
| --- | --- | --- |
| `local_clusters` | independent Uniform(0.002,0.007) | Select two different anchor edges uniformly. For pair `(e,f)`, weight is `[0.002 + sum_anchor exp(-(L1(center_e,anchor)+L1(center_f,anchor))/2)] * exp(-(distance(e,f)-1)/2)`. Nonzero `cross ~ Uniform(0.010,0.035)`. |
| `distant_pairs` | independent Uniform(0.002,0.007) | Weight one for edge distance at least 3, zero otherwise. Nonzero `cross ~ Uniform(0.010,0.035)`. |
| `anticorrelated` | independent log-uniform on [0.0015,0.010] | Weight `(0.022-base_e-base_f)**2`. Nonzero `cross = Uniform(0.010,0.025)+0.010*(1-(base_e+base_f)/0.020)`, hence inside [0.010,0.0335]. Low isolated-error edges are more likely to interact and interact more strongly. |
| `spam_drift` | independent log-uniform on [0.0015,0.010] | If there are `P` candidate pairs, define `v=exp(-(distance-1)/1.3)+0.05`. Weight `0.5/P+0.5*v/sum(v)`; nonzero `cross ~ Uniform(0.010,0.035)`. The SPAM drift below is enabled. |

Weights are normalized before sampling. Anchors, bases, support and nonzero
values are unknown even though the family ID is supplied. Anticorrelation here
is between base errors and crosstalk, **not** unobservable forward/inverse gate
asymmetry. Unconstrained inverse-layer asymmetry could not be identified from
these paired mirror measurements and is intentionally not part of the task.

## SPAM, including identifiable drift

All families independently draw `spam_intercept ~ Uniform(-0.4,0.4)`, one
`spam_edge_e ~ Uniform(-0.9,0.9)` per edge, and
`spam_density ~ Uniform(-1,1)`. Let `k=|M|` and

```
context = (shots_used_before_request + shots/2) / 2000
latent = spam_intercept + sum_{e in M} spam_edge_e/sqrt(max(1,k))
         + spam_density*k/floor(n/2) + drift(context)
A(M,context) = 0.58 + 0.37/(1+exp(-latent))
```

Thus `0.58 < A < 0.95`. For the first three families `drift=0`. In `spam_drift`,

```
drift(t) = amplitude*sin(2*pi*frequency*t + phase) + slope*(t-0.5)
amplitude ~ Uniform(0.4,0.9)
frequency ~ Uniform(0.5,1.5)
phase ~ Uniform(0,2*pi)
slope ~ Uniform(-0.8,0.8)
```

SPAM is constant within a shot batch at its disclosed midpoint and independent
of depth. Its smooth drift is tied to spent shots, not wall time, query count,
matching identity hashing, or a hidden phase reset. Layer errors do not drift.
The available depths and repeated matching contexts identify decay separately
from this nuisance; no arbitrary unobservable per-depth nuisance is present.

## Target distribution and scoring

Before any experiment, generate 96 distinct matchings of size `floor(n/2)-1`.
Their positions cycle between three kinds: no forced edges; a uniformly chosen
candidate edge-pair at distance at most 2 forced present; a uniformly chosen
candidate pair at distance at least 3 forced present. These choices depend only
on public graph geometry, not crosstalk support or error values.

For each draw, block forced vertices and find a maximum matching in the
remaining bipartite grid by randomized augmenting paths: shuffle each black
vertex's neighbors, visit black vertices in random order, and run recursive
augmentations. Uniformly subsample its resulting edges to the required size,
retaining the forced pair. Reject insufficient-size or duplicate results and
retry the same kind with a newly chosen forced pair (at most 10,000 tries).
`Grid.matching` specifies the exact ordering. This is not a claim of uniform
sampling over all grid matchings. Each target is one edge denser than the
largest legal query, so direct target measurement is impossible.

There are 12 hidden episodes, one for every family/shape combination. For a
family with 288 predictions, compute the mean of
`((prediction-rate)/(0.003+0.10*rate))**2` and set `score=1/(1+mean)`.
Report the arithmetic mean and minimum of the four family scores. Fixed pass
targets are mean >= 0.50 and minimum >= 0.3902439024390244, with all episodes
valid and isolated. A normalized RMSE of 1 in every family meets the mean
target; the worst-family threshold corresponds to normalized RMSE 1.25.
The additive scale prevents an unrealistic near-zero shot-noise requirement.
Time/shot resource usage is reported separately, not traded for accuracy.
The resource score is `max(0,1-0.5*min(1,u))` for valid runs, otherwise zero,
where `u` is the largest per-episode utilization of shot, request, wall or CPU
limits. Peak RSS is also reported. No unpublished thresholds are applied.
