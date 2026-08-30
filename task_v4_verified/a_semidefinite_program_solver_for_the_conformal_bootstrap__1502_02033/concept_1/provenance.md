# Private provenance and scope

Inspected primary sources on August 28, 2026:

- https://arxiv.org/html/1502.02033 — David Simmons-Duffin, *A Semidefinite Program
  Solver for the Conformal Bootstrap*, §§2.2 and 2.6. Pointwise polynomial
  constraints motivate the nodes; precision leakage motivates conditioning.
- https://arxiv.org/html/2509.14307v1 — Chang, Dommes, Kravchuk, Poland, and
  Simmons-Duffin, *Accurate bootstrap bounds from optimal interpolation*, version 1,
  September 17, 2025, §§3.1–3.3 and 4. Weighted Lebesgue amplification and equilibrium
  interpolation supply the conceptual starting point, not a claimed guarantee
  about finite-degree robust shared-node optimization.

The benchmark retains exponential/rational weights, rather than substituting
compact-support polynomial weights. Its extension is robust minimax control
over explicitly supplied uncertain prefactors with one shared finite node set.
Four families isolate damping sensitivity, nearly repeated near-boundary poles,
well-separated clusters, and changes in pole count/model. These are controlled
synthetic numerical problems, not measured conformal-block or SDPB speedups.

Our public baseline optimizes finite weighted Vandermonde energies under several
mixtures, then chooses a scale by a finite robust probe. It is deliberately
stronger than equally spaced or arbitrary-cutoff nodes, while leaving full
finite-degree worst-peak optimization to the participant. No full asymptotic
density formula, paper text, source dump, URL, or hidden case is in the public
export. The numerical verifier is independently implemented with derivative
bounds and a decreasing-tail argument; it imports no baseline or participant code.

Only baseline calibration and evaluator adversarial tests are generation-worker
evidence. No fresh attempt or hard difficulty classification is authorized here.
