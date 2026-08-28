# Solution-gap search and pre-pilot selection

Research cutoff: 2026-08-27 (America/Los_Angeles). Target: arXiv:1101.2646v4, 2011-05-23. These are hypotheses to test, not claims that every candidate is hard. No pilot is rejected on predicted agent ability alone.

## A — historical nonlinear uncertainty bugs [selected: c01_stats]
- Starting artifact: legacy ALPS Alea statistics, including the historical `simpleobsdata.h` behavior and a runnable, deliberately limited iid analysis adapter; no later covariance/propagation implementation.
- Private artifact: later ALPSCore Alea batching, covariance, and jackknife propagation; the December 2013 upstream report of a jackknife bug and repository history supply provenance.
- Outcome: scientifically correct joint uncertainty for nonlinear observables assembled from correlated, signed measurements and independent replicas.
- Shortcut: use `std/sqrt(N)` or independently propagate scalar standard errors.
- Why it fails: long correlation times and shared denominators change uncertainty and cross-covariance without changing marginal means.
- Independent bottlenecks: preserve sample/replica alignment and weighting; propagate nonlinear joint uncertainty; account for temporal dependence without unbounded memory.
- Check: fixed-sample independently computed reference statistics plus controlled processes with known moments; score means and joint covariance separately.
- Sources: https://lists.phys.ethz.ch/hyperkitty/list/comp-phys-alps-users%40lists.phys.ethz.ch/2013/12/ ; https://github.com/ALPSCore/ALPSCore ; https://alpscore.org/doxygen_snapshot/html/namespacealps_1_1alea.html

## B — original DMRG/TEBD to later general MPS [selected: c03_mps]
- Starting artifact: 2011 DMRG/TEBD interface and small exact-diagonalization baseline, not the later MPS code.
- Private artifact: ALPS MPS release accompanying arXiv:1407.0872; independent, pinned TeNPy implementation for expensive reference computations.
- Outcome: finite-system ground-state spectroscopy and nonlocal observables across genuinely different local Hilbert spaces and Hamiltonians.
- Shortcut: sparse exact diagonalization, product states, or a table of uniform-chain energies.
- Why it fails: realistic chains/ladders have exponentially large Hilbert spaces, inhomogeneity, and model-dependent correlations; an energy-only fit does not give the other observables.
- Independent bottlenecks: construct correct operators and conserved sectors for different physical families; converged variational optimization; contractions and sector spectroscopy.
- Check: stored, convergence-tested MPS outputs; small exact checks; independent scores for energies, gaps, and correlations where the final pilot contract includes them.
- Sources: https://arxiv.org/abs/1407.0872 ; https://github.com/ALPSim/ALPS/tree/master/applications/dmrg/mps ; https://github.com/tenpy/tenpy/tree/v1.0.6

## C — realistic-scale extended-ensemble sampling
- Starting artifact: fixed-temperature/local-update or early Wang–Landau sampler and original lattice definitions.
- Private artifact: official ALPS `qwl` extended-ensemble implementation and the quantum Wang–Landau method, arXiv:cond-mat/0207138.
- Outcome: free-energy/entropy differences and barrier-spanning thermodynamics through a first-order regime.
- Shortcut: independent Metropolis runs or a fixed flat-histogram schedule.
- Why it fails: exponentially slow tunneling and normalization across disconnected sampled energy windows.
- Independent bottlenecks: ergodic updates across a barrier; density-of-states normalization; uncertainty under adaptive sampling.
- Check: expensive official-code density-of-states references and thermodynamic consistency, rather than just local energy.
- Not built: references are feasible but stochastic runtime calibration is more expensive than the selected minimal pilots; this is not an agent-difficulty rejection.
- Sources: https://arxiv.org/abs/cond-mat/0207138 ; https://github.com/ALPSim/ALPS/tree/master/applications/qmc

## D — segment impurity solver to complex multiorbital interactions
- Starting artifact: density-density/segment impurity solver in the original release.
- Private artifact: ALPSCore CT-HYB for general instantaneous two-body interactions and complex hybridization, arXiv:1609.09559.
- Outcome: matrix Green functions for spin-orbit/orbital-mixing impurity families.
- Shortcut: diagonalize the hybridization once or discard off-diagonal entries, then use independent segment solvers.
- Why it fails: frequency-dependent hybridization matrices and local interactions need not share an eigenbasis; non-density interactions invalidate segment factorization.
- Independent bottlenecks: general local trace; complex fermionic signs; low-variance matrix measurements and stable determinant updates.
- Check: small-impurity exact Lehmann tests and expensive published-code reference runs, including covariance under basis rotation.
- Not built: compiling and validating the full stochastic solver is a larger reference project; no empirical difficulty claim.
- Sources: https://arxiv.org/abs/1609.09559 ; https://github.com/ALPSCore/CT-HYB

## E — real spin-ladder model discrepancy
- Starting artifact: isotropic spin-ladder susceptibility tutorial and measured susceptibility data, if redistributable raw data can be acquired.
- Private artifact: cited work on Na2Fe2(C2O4)3(H2O)2 including uniaxial anisotropy and additional measurements.
- Outcome: joint prediction of susceptibility and field response, not a one-curve exchange fit.
- Shortcut: fit a rescaled isotropic ladder curve plus a Curie tail.
- Why it fails: anisotropy and inter-ladder/ordering effects can appear differently in temperature and field data; fitting one curve cannot establish the model.
- Independent bottlenecks: identify model discrepancy; quantify identifiable parameters; simulate the revised physical family.
- Check: genuinely held-out measured observables with experimental error bars.
- Not built: raw machine-readable observations and a validated privileged fit were not established during initial inspection. Synthetic data must not be mislabeled real.
- Sources: https://github.com/cmsi/alps-tutorial/blob/master/overview/overview-en.tex ; https://eprints.soton.ac.uk/20258 ; https://alps.comp-phys.org/tutorials/mcs/mc02/

## F — interacting DMFT pipeline faults [selected: c02_dmft]
- Starting artifact: pre-fix ALPS DMFT Fourier/Hilbert/solver handoff implementation.
- Private artifact: exact upstream corrections including `2fa76e234a64cefa0ccb00a7b82b0d85a2f3023e` (all AFM flavor pairs), `e2e9e16e` (off-diagonal Fourier guard), `18d8474e` (external solver output), and `8d3522b7` (solver selection).
- Outcome: consistent imaginary-time/frequency, multiband antiferromagnetic self-consistency, and solver dispatch behavior.
- Shortcut: patch the first failing line, or hard-code one-band/scalar formulas.
- Why it fails: one-band diagonal tests do not expose skipped flavor pairs, matrix tails, or inconsistent handoffs.
- Independent bottlenecks: transform conventions/tails; flavor-pair lattice integration; protocol/solver consistency. Only genuinely scientific components enter core scoring.
- Check: analytic pole transforms, independent quadrature, and end-to-end invariant checks on held-out multiband systems.
- Sources: https://github.com/ALPSim/ALPS/pull/102 ; https://github.com/ALPSim/ALPS/commit/2fa76e234a64cefa0ccb00a7b82b0d85a2f3023e

## G — missing sign and covariance ablations
- Starting artifact: legacy CT-HYB Legendre measurement and scalar uncertainty reporting.
- Private artifact: upstream `272d6e35` applies the Monte Carlo sign once in `measure_Gl`; later Alea preserves joined covariance.
- Outcome: reconcile time, Matsubara, and Legendre measurements when the average sign is nontrivial, with an ablation that separates sign bias from noise.
- Shortcut: test only positive-sign data or compare the mean of unsigned measurements.
- Why it fails: the affected branches are identical in the sign-free limit but not at nontrivial sign; extra sampling cannot remove systematic bias.
- Independent bottlenecks: signed estimator normalization; transform/basis normalization; covariance-aware consistency testing.
- Check: deterministic signed-event fixtures against the fixed official estimator, plus independent transforms and sign-free controls.
- Not built separately: overlaps the statistics/integration bottlenecks already represented by c01 and c02; retained as a source-grounded challenge direction, not a fifth pilot.
- Source: https://github.com/ALPSim/ALPS/commit/272d6e35

## H — resolution versus causality in matrix continuation [selected: c04_continuation]
- Starting artifact: scalar continuation/DMFT output interface with a weak diagonal-only or direct rational baseline.
- Private artifact: matrix Carathéodory continuation (arXiv:2107.00788), official TRIQS/Nevanlinna implementation, and high-quality real-axis references computed from private Hamiltonians.
- Outcome: full matrix real-frequency Green functions and a Dyson-related observable, retaining off-diagonal structure and causality across finite spectra and smooth bands.
- Shortcut: scalar Padé per element, discard off-diagonals, or unconstrained fixed-degree least squares.
- Why it fails: matrix positivity is not entrywise positivity; near singular Dyson inversion amplifies continuation errors; finite poles and continua need different regularization decisions.
- Independent bottlenecks: stable analytic reconstruction; matrix causal structure and moments; nonlinear matrix Dyson consistency. Identifiability must be checked rather than assumed.
- Check: stored broadened resolvents from known private Hamiltonians, independent direct matrix-inverse checks, basis-rotation tests, and continuous error scores. Reject any purported hard region explained only by unrecoverable data.
- Sources: https://arxiv.org/abs/2107.00788 ; https://arxiv.org/abs/2010.04572 ; https://github.com/TRIQS/Nevanlinna ; https://triqs.github.io/Nevanlinna/latest/tutorials/hubbard_square_non_int.html

## Anti-compression decisions before pilot construction

| Pilot | Can one fixed generic kernel solve all cases? | Why the pilot is still worth testing |
|---|---|---|
| c01_stats | A correct general statistical library could; a scalar iid kernel cannot. | Independent temporal-dependence and nonlinear joint-propagation/replica bottlenecks. Empirical pilot decides whether this is nevertheless easy. |
| c02_dmft | A single transform/inverse kernel cannot implement the pipeline. | Interacting physical-convention and multiband self-consistency faults in different modules. |
| c03_mps | A sufficiently general MPS package could. | Realistic exponential Hilbert-space size defeats dense/direct methods; sector preparation, optimization, and distinct observables are separately checked. |
| c04_continuation | A powerful general matrix continuation package might. | Finite-pole versus continuum decisions plus independently checked matrix/Dyson structure. Explicit shortcut testing and identifiability audit are mandatory. |

All four receive one isolated empirical attempt before tournament elimination. TASK.md contains a mission and interface pointers, never this document or the solution-bearing source.

## Post-pilot findings and attribution corrections

The briefs above preserve the pre-pilot hypotheses; they are not retroactive proof of missing capabilities. Inspection of the complete original paper confirms that ALPS 2.0 already included binning, jackknife cross-correlation analysis, and Python exposure. Candidate A's built pilot consequently represents an authored deficient adapter plus a participant-hidden later-library oracle, not a demonstrated introduction of jackknife after 2011. Candidate B's spin/boson adapter likewise does not establish that the physical families were absent from the 2011 release. Exact fixes and authored conventions are distinguished in `REPORT.md` and the private provenance records.

All four fresh submissions solve their hidden core and challenge families. A general weighted vector jackknife compresses A; F/G are fully repaired; a charge-conserving DMRG implementation solves B; and an adaptive matrix-rational portfolio solves H. Source-grounded critical-chain and intrinsically complex-band stress tests also succeed. None is accepted, and no natural reference-success/submission-failure region supports a ratchet. Full scores and the zero-ratchet/zero-second-attempt decision are in `REPORT.md` and `selection.json`.

A late source audit also follows the MPS ancillary README to the complete author archive, DOI `10.6084/m9.figshare.1092509`. Its seven Hubbard runs vary bond dimension for one 192-site Hamiltonian and particle sector. They are valuable privileged convergence outputs, but are not seven distinct physical held-out cases. No fifth concept is built from this late discovery, and an out-of-contract Hubbard input is not graded as a failure of the spin/boson pilot. The archive and its audit remain available under `private/sources/supplement_audit/`.
