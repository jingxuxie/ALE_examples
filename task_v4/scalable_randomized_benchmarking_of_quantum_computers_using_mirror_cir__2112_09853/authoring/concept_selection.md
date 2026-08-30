# Private discovery record

This directory is generation-only and must never be mounted for participants.
The referenced work is Proctor et al., arXiv:2112.09853v2, including its supplement.
The task extensions are benchmark problems, not claims made by the paper.

## Concepts considered before construction

1. Exact Hamming-histogram polarization and exponential fitting (A): rejected;
   essentially direct implementation of the paper's equations.
2. Reproduce scalable Clifford mirror generation from pyGSTi (F): rejected;
   source-package reproduction without a compelling empirical optimization gap.
3. Repair stochastic two-qubit drops in mirror compilation (F): considered using
   official issue 844; too narrow alone, with substantial source-disclosure risk.
4. Correlated telemetry Bayesian portfolio deployment (A): rejected after review
   of the local previous package. Six fresh attempts scored 100/100, including
   its adaptive/minimax generation; extra graphical-model machinery is not
   evidence of difficulty and the link to the paper is weak.
5. Estimate true layer infidelity from finite-shot, nonexponential MRB traces (D):
   promising, but latent-noise identifiability requires care before using accuracy
   as a trustworthy difficulty criterion.
6. Predict held-out historical processor histograms (D): considered from the
   authors' released data; small numbers of independent processors and temporal
   calibration shifts make a defensible train/test target difficult.
7. Optimize layer sampling for balanced edge coverage and rapid scrambling (A):
   promising, but simple convex marginal-balancing versions are too standard.
8. Construct shallow native Clifford blocks with worst-case low-weight Pauli
   spreading, including inverse blocks (C): selected for exact verification and
   a genuine discrete resource frontier relevant to the paper's scrambling
   condition.
9. Adaptive identification of context-dependent crosstalk using budgeted noisy
   mirror experiments (E): selected for nonlinear observations, nuisance SPAM,
   structured interactions, and a worst-family generalization objective.
10. Constrained Markovian-noise falsification of an MRB inference surrogate (B):
    selected subject to exact-channel validation, nontrivial admissibility
    constraints, and a fixed witness target before any fresh attempt.

At most three concepts are constructed. Targets and participant hashes are
frozen before the corresponding first attempt. Fresh solving uses only
`run_allowlisted_codex.sh --model ultima-alpha --task-read-only`, never these
generation notes, previous submissions, private solvers, or hidden challenges.

## Primary-source inspection

- Paper and supplement: `sources/paper.pdf`; exact local Pauli error models,
  inverse-layer covariance, cancellation, and required local scrambling.
- Authors' data/code: Zenodo record 5176787, `sources/supplement.zip`.
- Official implementation: sandialabs/pyGSTi, `sources/randomcircuit.py`.
- Official issue 844: stochastic two-qubit drops in mirror construction,
  `sources/issue_844.json`.
- Official releases and MCFE follow-up PR 628 inspected via the web.
- Universal-gate follow-up arXiv:2207.07272 and Qiskit experiment PR 842 inspected
  for protocol differences rather than treated as participant assets.
- Previous local package `tasks/...2112_09853/status.json` and fresh v_06 code
  inspected; no previous implementation is a passing solution to these concepts.
