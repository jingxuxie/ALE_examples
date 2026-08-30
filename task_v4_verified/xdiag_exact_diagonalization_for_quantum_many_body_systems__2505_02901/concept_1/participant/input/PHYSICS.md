# Spin dynamics and expected loss

The benchmark extends the symmetry-aware spin-half dynamics and entropy
calculations in *XDiag: Exact Diagonalization for Quantum Many-Body Systems*,
arXiv:2505.02901, and the earlier Sector Relay II numerical challenge. Fleet
manufacturing and diagnostic decisions are a benchmark construction, not a
claim or result from that paper.

For an even ring of `L` sites, use ascending integer bitmasks with exactly
`nup` occupied sites. Bit `i` is spin up; `z_i = n_i - 1/2`. With periodic
indices, regime `q` has the Hamiltonian

```
H_q(t) = sum_i f_q(i,t) [J1xy/2 (S+_i S-_(i+1) + S-_i S+_(i+1))
                        + J1z z_i z_(i+1)]
       + q.j2_multiplier sum_i [J2xy/2 (S+_i S-_(i+2) + S-_i S+_(i+2))
                                + J2z z_i z_(i+2)]
f_q(i,t) = 1 + (-1)^i [delta*q.delta_multiplier
                      + drive_amplitude*q.drive_multiplier
                        * sin(drive_omega*q.omega_multiplier*t)].
```

Both sums run over all sites once. All rings have `L>=6`, so each displayed
sum includes each unordered bond once. Units set hbar to one. The initial
state is the computational basis state `initial_up_sites`; all evolution
obeys `d psi/dt = -i H_q(t) psi`.

The unobserved regime persists through the entire experiment. Each named
prior scenario supplies a different probability distribution on that same
regime. The scenario label is not observable and cannot affect the policy.

An open policy applies a manufactured diagonal action at `open_loop_time`,
then evolves to `t_final`. A probe policy first observes the calibration
result. Its likelihood depends only on the persistent regime and it does not
disturb the spin state. For each result, the policy selects a first sensor.
At its time, measure the spectral projectors of its site permutation:

```
T |n_0,...,n_(L-1)> moves the spin at i to permutation[i], with no sign;
P_k = (1/K) sum_(r=0)^(K-1) exp(-2*pi*i*k*r/K) T^r,  k=0,...,K-1.
```

The declared order `K` is the permutation order. Sensor permutations commute
with every regime Hamiltonian. Born probabilities and normalized collapsed
states are used. Immediately after first outcome `k`, apply the prescribed
bridge `exp(-i sum_i bridge_phase_by_sector[k][i] n_i)`. This kick generally
breaks the symmetry. Select a later second sensor separately for every first
outcome, evolve, measure its sectors, and apply the chosen terminal action
`exp(-i sum_i action.phase[i] n_i)`. No second-sensor bridge is applied.
Evolve the final state to `t_final`.

For each normalized final pure state, embed its amplitudes in the full
bipartite coefficient matrix with row sites `entropy_sites` (in listed order)
and the remaining column sites in ascending order; absent fixed-magnetization
configurations have zero amplitude. Let `S_A` be its natural-log von Neumann
entropy. The loss is

```
m_stag = (2/L) <sum_i (-1)^i z_i>
loss = 1 - S_A / log(2^min(len(entropy_sites), L-len(entropy_sites)))
       + imbalance_weight * m_stag^2.
```

Compute this nonlinear loss separately for each regime and quantum outcome,
then average the losses, not the states, density matrices, or imbalances.
If `C[q,k,l,a]` is a route catalog numerator, the contribution of a leaf with
calibration result `r`, first sector `k`, second sector `l`, and action `a`
to scenario `s` is `sum_q prior_s[q] * likelihood_q[r] * C[q,k,l,a]`.
This accounts for both measurement updates without explicitly normalizing
Bayesian posteriors. Sum every leaf to get the scenario expected loss.

There is no Monte Carlo in the supplied catalogs. They were integrated in the
fixed-magnetization Hilbert space; absolute catalog error below `2e-7` is
irrelevant at the quality targets. The official scorer independently evolves
submitted routes from the raw Hamiltonian rather than trusting these catalogs
or any participant-reported loss.
