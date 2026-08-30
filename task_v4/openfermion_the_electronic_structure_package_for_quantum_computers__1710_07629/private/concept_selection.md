# Privileged concept selection

Nine concepts were considered before the first tournament. Three were built,
using three distinct primary verification modes. This file and all research
artifacts remain outside the participant allowlists.

| Concept | Mode | Decision and substantive difficulty |
|---|---|---|
| Joint orbital/auxiliary LCU-gauge compression | A | Built: coupled nonconvex sparse representation search against a spectral-candidate baseline; both gauges affect the explicitly defined coefficient cost. |
| Sparse hardware-local Gaussian state synthesis | C | Built: mixed discrete routing and continuous inverse synthesis below generic exact compiler budgets; privately planted circuits validate feasibility. |
| Correlated Hubbard charge and spin gaps | D | Built: interaction-sensitive held-out prediction/amortized computation, with private sector-exact labels and a declared inference budget. |
| Joint low-rank truncation, Trotter ordering and routing | A | Reserve: promising but difficult to separate tensor residual, true propagation error and routing costs reliably within generation time. |
| Coefficient norm versus actual measurement-cost counterexamples | B | Reserve: scientifically meaningful, but small counterexamples may collapse to standard numerical search and protocol-specific algebra. |
| Compact fermionic sum-of-squares certificates | C | Reserve: meaningful certificate-size search, but basic variants reduce to one SDP or package invocation. |
| Active measurements on a hidden correlated state | E | Reserve: valid only with actual hidden outcomes, not a deterministic public uncertainty proxy; larger simulator construction risk. |
| Basis-convention, spin-ordering and sector repairs | F | Reserve: physical invariant tests are trustworthy, but common variants simply reproduce known source behavior or isolated bug fixes. |
| Active acquisition of costly Hubbard labels | E | Reserve: distinct real query tradeoff, but overlaps the selected prediction concept and would consume a fourth build. |

## Source and prior-attempt review

The seed paper's numerical testing, orbital transformations, Gaussian-state
preparation and Hubbard models directly motivate the selected tasks. Official
OpenFermion code, releases, issues, low-rank tutorials and FQE follow-ups were
reviewed. Relevant follow-ups include arXiv:2103.14753 (orbital coefficient-norm
optimization), arXiv:2212.07957 (regularized compressed double factorization),
and arXiv:2603.05675 (modern matchgate constructions). These do not supply
complete solutions to the custom constrained objectives.

Existing local OpenFermion attempts in `tasks/openfermion_.../` were inspected
privately. The v01 and v02 measurement-grouping tasks scored 100: the reported
geometric objective/reference ratios were 0.2661 and 0.6803. Their successful
submissions eliminated shot allocation analytically and combined familiar
grouping/local-search methods. A v03 timeout alone was not treated as evidence
of scientific hardness. None of these submissions is exposed to new agents.

## Evaluator safeguards and target calibration

The gauge objective is explicitly a coefficient-based LCU proxy, not the Pauli
norm of the fully recombined Hamiltonian and not an eigenvalue-based DF norm.
Thus neither chosen gauge is a null optimization variable. Full Fock-sector
spectra are independently checked under both transformations. No tensor
truncation is allowed.

Initial planted gauges did not establish a large gap over the spectral baseline;
an untested 75-percent target was discarded before the fresh tournament. The
final target is 25-percent aggregate and 10-percent worst-family reduction.
A separate private smooth-manifold portfolio subsequently achieved 44.519%
aggregate and 25.895% worst-family reduction in 48.915 seconds under the actual
180-second inference sandbox. No target was changed after launching the agent.

Circuit witnesses are compared to the complete covariance and Slater-state
fidelity, not just energy or the planted parameter list. Any equivalent legal
witness is accepted. Prediction labels must be full sector-exact results,
with convergence checks; fixed-Sz spin differences must not be mislabeled as
certified total-spin gaps.
