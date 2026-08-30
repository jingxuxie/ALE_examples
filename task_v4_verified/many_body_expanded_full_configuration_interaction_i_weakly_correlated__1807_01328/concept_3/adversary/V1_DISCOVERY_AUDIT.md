# Private discovery-quality audit: v1 inverse shortcut

**Disposition:** the difficulty concern is substantiated. On 100 independent accepted models, v1 reduces to independent singleton/pair inversions followed by one small diagonalization. Rare multiple roots exist on the sampler's accepted support, but the constructed example needs only local triple checks, not combinatorial search. This is a strong reason not to retain v1 as the final hard predictive-science task if the same method passes the mandatory post-fresh champion check.

The launched generation is untouched. No released feature/label arrays were parsed for inference, no hidden predictions were generated, and no new participant generation or training dataset was built. Public and evaluator files were hashed before and after; all were unchanged. Only private files under `adversary/` were added or amended. The older local-identifiability note established neither discovery difficulty nor resistance to inverse reconstruction; its triangular structure is precisely the shortcut demonstrated here.

## 1. Quantitative independent-draw result

`v1_inverse_audit.py` draws 100 independent accepted Hamiltonians with deterministic size/family stratification and independent private audit randomness. Family counts are 17/17/17/17/16/16, including both unlabeled families. Source amplitudes are inferred from supplied singleton energies and public profiles/diagonals, not read from the source Hamiltonian. Pair magnitudes are then inferred from supplied pair energies and signs. The source Hamiltonian is consulted only to measure reconstruction error.

| Check | Result |
| --- | ---: |
| Independent accepted models | 100 |
| Pair-energy curves checked over the full magnitude interval [0.012, 0.28] | 2,460 |
| Positive-sign pair curves | 1,060 |
| Curves with an interior turning point | 0 |
| Models / edges with multiple roots | 0 / 0 |
| Models requiring triple observations for inference | 0 |
| Models requiring global branch search | 0 |
| Maximum recovered source-amplitude error | 5.06e-14 |
| Tail RMSE | 9.4931e-14 synthetic Eh |
| Maximum tail absolute error | 3.9014e-13 synthetic Eh |
| Total inversion time, 100 models | 2.075 seconds |
| Initial generation, inversion and support-probe audit time | 5.732 seconds |

These errors are vastly below the frozen 3e-5 / 6e-5 accuracy limits. They are **not** scores on the launched hidden set. Zero ambiguities in 100 stratified models is empirical evidence, not a proof that every sampler draw is unambiguous. The supplementary check of the alternative support branch is recorded separately in the JSON and is not included in the initial runtime.

### Why the shortcut is even simpler than the implementation

A singleton CAS is an arrowhead matrix: one reference state couples to the O possible occupied holes, with no occupied–occupied transfers. Write its correlation as c_v<0, public replacement gaps as d_iv, public normalized occupied profile as u_i, and unknown source amplitude as a_v. Eliminating the hole amplitudes gives

`a_v^2 = -c_v / sum_i[u_i^2 / (d_iv - c_v)]`.

Thus singleton recovery has a closed form. The audit conservatively used bracketed scalar roots instead. Once these amplitudes are fixed, each pair CAS contains only one remaining unknown virtual-edge magnitude. Neither data training nor extrapolation across families is needed on the observed monotone branches. Not exposing a full matrix directly is therefore not a meaningful computational obstacle in v1.

## 2. Multiple positive roots do exist, but are not enough

For one edge magnitude m, the pair matrix is H(m)=H0+mD. Its ground energy is the minimum over unit vectors of an affine function of m, hence concave. On a generic nonflat curve there are at most two roots of a fixed energy level. The audit uses Hellmann–Feynman endpoint slopes, finds an interior maximum when needed, and brackets roots on both monotone branches; it does not rely on a grid missing a narrow second root.

A deliberately extreme **non-IID support probe**, excluded from the empirical rates, gives two positive roots for virtual edge (0,1):

- Magnitudes **0.1800000000000108** and **0.2683108816566140**; both lie in [0.012,0.28]. The maximum is at about 0.2246589164.
- Singleton energies are identical; pair energies differ by at most **1.95e-16**.
- Both complete Hamiltonians satisfy release curation: reference probabilities **0.9050071 / 0.8995388**, absolute tails **9.64109e-4 / 1.075845e-3**, and minimum gap **0.811**.
- Triples distinguish them: maximum triple-energy difference **1.84233e-4**. Four affected triple constraints require only eight tiny CAS solves; the smallest rejected triple mismatch is **1.48044e-4**, versus a 1e-10 compatibility tolerance.
- Local domain propagation selects the correct root. There is one ambiguous edge, two raw assignments, and **no global branch search**.

The JSON records a constructive support witness: 2 pairs, 6 virtuals, repulsive family, source amplitudes [0.30,0.07,0.07,0.07,0.07,0.07], public diagonal data, and the edge magnitudes. A shared virtual-energy scale of 0.855 places all virtual onsite draws inside their specified interval. Clipped source extrema and positive edge magnitudes are permitted by the lognormal priors. This is a rare support example, not evidence that ambiguity is common.

In principle m ambiguous edges give 2^m raw assignments, but each observed triple constrains at most three edge choices (at most eight local combinations). Many raw branches do not establish computational hardness: constraint propagation can eliminate them cheaply. Neither this probe nor the 100 independent models demonstrate genuinely combinatorial branch selection.

## 3. Same-mode ratchet sketch only: hidden independent source profiles

Keep the seniority-zero pair-conserving Hamiltonian, visible diagonals/gaps and known signs, 2–3 pairs, 6–9 virtuals, low-order CAS observations, independent labeled training/validation, and fixed static hidden predictions. Replace the shared known source profile with **independent hidden positive occupied–virtual profiles**: each column has its own direction and norm, and the source-transfer matrix generically has rank O rather than one. Do not publish these profiles or the per-column norms. Keep occupied–occupied transfers zero initially and avoid arbitrary hidden sign fluxes or higher-body terms.

This leaves O*V + choose(V,2) continuous transfer magnitudes. The independent low-order scalar observations number V + choose(V,2) + choose(V,3). CAS energies and their inclusion–exclusion increments must **not** be counted twice.

| Virtuals V | Unknowns, O=2 | Unknowns, O=3 | Low-order observations |
| ---: | ---: | ---: | ---: |
| 6 | 27 | 33 | 41 |
| 7 | 35 | 42 | 63 |
| 8 | 44 | 52 | 92 |
| 9 | 54 | 63 | 129 |

The necessary count condition holds, but it does not prove identifiability. Required pre-release audits for a future ratchet:

1. Use known nondegenerate occupied diagonal splittings and heterogeneous diagonal interactions to avoid source-rotation or permutation symmetries. Preserve weak-correlation and nonnegligible-tail checks.
2. Form the Jacobian of all unpadded order-1/2/3 CAS energies with respect to the actual hidden transfer parameters, preferably by Hellmann–Feynman derivatives, cross-checked at two finite-difference step sizes. Examine scaled singular values on independent cases from every family and size. Count active-bound constraints correctly; do not declare rank from a loose default tolerance.
3. Test **target identifiability**, not only parameter rank: seek bounded perturbations along weak/null singular directions that preserve low-order features at their stated precision but move the tail beyond the proposed accuracy tolerance. Run multistart inverse fits and compare the full tails of distinct feature-compatible solutions.
4. If materially different tails remain observationally indistinguishable, narrow the generator support or add justified coupled low-order observables, then repeat the audits. Do not manufacture hardness by withholding indispensable information. Avoid source-resolved singleton occupation probabilities: they can reveal the individual source transfers directly and restore an easy shortcut.
5. Run a strong inverse-reconstruction champion search before declaring the ratchet hard. Conditional on source directions, norms and edge magnitudes may still be eliminated with scalar inversions; the remaining joint problem can have only (O−1)*V = **6–18** source-direction degrees of freedom. Variable projection plus multistart nonlinear least squares may still solve it cheaply. Rank>1 alone is **not** a discovery-quality guarantee.

No rank>1 generator, dataset, thresholds, or new concept has been built or tested here. Any later release requires explicit authorization, scientific sufficiency checks, realistic inverse and learning baselines, and a new target freeze before a fresh launch.

## 4. Required next gate after the fresh result

Run the scalar-inverse candidate against the unchanged launched target through the authorized private champion procedure. If it passes, record the champion and treat v1 as an inverse-reconstruction exercise rather than the requested final hard discovery task. Keep the ongoing fresh attempt and all current frozen artifacts intact. This audit supplies a concrete vulnerability and a candidate direction for a ratchet; it does not itself claim a passing launched-set score.

Artifacts: `v1_inverse_audit.py` (private audit implementation), `v1_inverse_audit.json` (metrics, independent audit seed, support witness, and preservation hashes), `v1_inverse_audit.log` (initial run output), and this note.
