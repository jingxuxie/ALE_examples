# Synthetic pair-conserving model

This benchmark uses the virtual-orbital many-body expansion idea, not molecular integrals, the paper's numerical results, or full spin-orbital electronic FCI. “Exact” means exact diagonalization **within this seniority-zero pair space**. Basis states occupy O of O+V spatial orbitals with pairs; the maximum dimension is binomial(12,3) = 220.

With pair occupation N_p∈{0,1} and pair creation P_p†, the real symmetric Hamiltonian is

`H = Σ_p e_p N_p + Σ_{p<q} U_pq N_p N_q + Σ_{p<q} t_pq (P_p† P_q + P_q† P_p)`.

Pair transfers have the displayed sign, without extra determinant-order signs, and conserve pair number. Diagonal e and U are public; the complete transfer matrix is **not**. There are no unknown three-body or higher-body Hamiltonian terms. Occupied–occupied transfers vanish. Occupied–virtual transfers are `t_iv = −u_i a_v`, with public positive normalized profile u and unknown positive amplitudes a_v. Virtual–virtual signs are public; magnitudes are not. Constrained latent structure and explicit signs avoid arbitrary invisible high-body terms or unobserved sign fluxes. Inferring missing magnitudes or their collective effect is part of the challenge; no high-order correction formula is supplied.

The reference occupies the first O orbitals. CAS subset S retains all O occupied orbitals plus virtuals in S, with O pairs. Its correlation is `C(S) = ground_energy(H_S) − reference_energy`, C(empty)=0. Connected increments satisfy `Δ(S) = C(S) − Σ_{nonempty T proper subset of S} Δ(T)`. The target is the sum of increments of order ≥4, equivalently full correlation minus the provided order-≤3 sum. This defines a label, not an extrapolation ansatz.

## Distribution

`generator.py` is the executable specification. Release sizes O∈{2,3}, V∈{6,7,8,9} are stratified. Occupied onsite energies are sorted Uniform(−0.35,−0.08); virtual energies are sorted Uniform(0.85,1.8) times a shared Uniform(0.85,1.35) scale. Symmetric density interactions average two Uniform(0,0.055) draws, with zero diagonal. Occupied profiles normalize independent Uniform(0.65,1.35) values.

Virtual positions are sorted Uniform(0,1), divided at the median into two groups. Occupied–virtual amplitudes multiply a Uniform(0.105,0.245) scale by independent lognormal(0,0.18) factors, clipped to [0.07,0.30]. Virtual–virtual magnitudes multiply a Uniform(0.055,0.15) scale, a family envelope, and independent lognormal(0,0.15) factors, clipped to [0.012,0.28]. A range parameter r is Uniform(0.20,0.65). Lognormal parameters describe the underlying normal. Finally all virtual-indexed arrays receive a common random permutation.

For distance d and same-group indicator g:

| Family | Transfer sign | Magnitude envelope |
| --- | --- | --- |
| coherent | negative | 1 |
| repulsive | positive | 1 |
| screened | negative | 0.25 + 1.10 exp(−d/r) |
| frustrated | negative if g, positive otherwise | 1 if g, 0.75 otherwise |
| mixed_range | negative if d<0.35, positive otherwise | 0.45 + exp(−d/r) |
| bottleneck | negative if g, positive otherwise | 1.35 if g, 0.25 otherwise |

Accept only full-ground-state reference probability ≥0.85, all single-replacement diagonal gaps ≥0.80, and |tail|≥1.5e−4. This **explicit label-conditioned curation** removes negligible targets and strongly mixed states. The task is conditional on those criteria, not an unbiased sample of all pair Hamiltonians. It contains sign-coherent and cancellation-dominated expansions; increments need not form a geometric sequence. Synthetic Eh is a numerical scale, not a chemical-accuracy claim.

## Independent training and baseline

You may use `sample_hamiltonian`, `low_order_features`, `label`, and `accepted_sample` with your own NumPy RNG to generate independent data, including in the two unlabeled families. None contains release seeds, fixed IDs, hidden Hamiltonians, or hidden targets. Full energies are affordable for **newly generated Hamiltonians**; test features omit the transfer amplitudes needed to call a full solver directly.

The baseline computes permutation-invariant low-order statistics, diagonal descriptors and increment-graph moments. It compares ExtraTrees (700 trees), histogram gradient boosting (600 steps), and quadratic RidgeCV on validation, then refits the winner on both labeled splits. Public seeds initialize models only. No fitted estimator is loaded by the evaluator. Physics-informed inference or justified extrapolation is welcome; no passing solution or convergence guarantee is provided.
