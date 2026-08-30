# Private physical phase search

This sidecar reviews an unchanged copy of the completed `attempts/v_2` solver.
It does not grade submissions, edit frozen assets, or use startup delays as
evidence of optimization difficulty. The portfolio evaluators were quiescent
before this search. The startup-only portfolio probe had 8.572 s outer wall,
0.359 s protected-worker wall, and 0.263 s solver CPU; two failed public probes
had no supervisor resource file. Main owns the launcher repair.

The phase seed is arXiv:1302.5582v3, Eq. (5), Sec. I D and Fig. 18. For uniform
coupling kappa, use lambda_eff=lambda4/kappa**1.5, massR2=lambda_eff/65, and
delta=lambda_eff*ellipk(4/(4+massR2))/(2*pi*sqrt(4+massR2)). The scan center is
kappa*(massR2-delta). This is only an infinite-lattice-inspired search seed,
not a finite-chain critical-point certificate or a ground-energy bound.
Provenance: `https://arxiv.org/pdf/1302.5582v3` (reviewed August 28, 2026).

The copied champion retains the entire requested local basis. Its default
schedule is three two-site sweeps followed by fixed-bond one-site sweeps.
The private teacher starts from its output, retains the same local dimension
and bond cap, and applies longer parity-preserving two-site and one-site
optimization. Every retained state is independently contracted. A positive
energy difference is an achieved variational improvement, not a proof of the
exact ground energy or of resource-feasible solvability.

`phase_scan.py` writes requests, states, CPU/wall observations, entanglement
spectra, Hamiltonian residual norms, cutoff populations, and same-sector
energy differences. These are generation-time in-process diagnostics, not
frozen evaluator scores. No original request target or reference is changed.
Run all scripts with `PYTHONDONTWRITEBYTECODE=1` and BLAS/OMP threads set to 1.

## Explicit weak-quartic proposals

arXiv:2104.10564v3, Sec. IV and Table I, distinguishes free-boson UV
central charge 1 from Ising IR central charge 1/2, with growing lattice
correlation length in the continuum limit. arXiv:1302.5582v3,
Sec. III A 2–4 / Figs. 6–8, motivates weak-quartic and local-cutoff
sensitivity checks. These are motivations, not finite-chain certificates.
The later paper uses a lambda/4 interaction: its critical ratios are NOT
transplanted into this task. All requests retain lambda4*phi4/24 and the
original ratio-65 seed remains heuristic.

Proposed lambda4=0.05–0.3 and N=48–64, cap=16–24 cases are explicitly
outside the initial sampling/range where applicable. They are not admitted
hidden cases and do not change any public or evaluator file. Provenance:
`https://arxiv.org/pdf/2104.10564` (reviewed August 28, 2026).

The first scaling teacher exposed greedy environment-einsum path fallback;
its pre-fix source and logs are retained. Only the private teacher's
environment contractions were replaced by sequential contractions, checked
against direct real and complex einsums. Champion source remains unchanged.

Final controls add a uniform 1e-5 field or a smooth sign-changing 1e-4 field
and a physical weak link. These field magnitudes overlap the existing private
extension distribution. Parity projection is only an initializer for tilted
cases: refinement uses the full original Hamiltonian in the unrestricted
sector, and all final energies are measured against that original request.
The bounded search stops at 20 candidates; no N96 or larger-cap extension is
needed to demonstrate the retained physical/latency gaps.
