# Solution-gap mining register

Date: 2026-08-27 (America/Los_Angeles). Target: arXiv:2001.00024v1,
submitted 2019-12-31; PRL 125, 030503 (2020). The regenerated HTML date is
not a new paper version. Only one arXiv version is listed.

This register distinguishes verified artifacts from proposed capability gaps.
An unavailable implementation is not a privately runnable reference. Author
reimplementations and new benchmark packaging are not represented as upstream
bug fixes. The old local ALE pilot is not a scientific source: its 600-second
timeout and missing policy artifact are not evidence of substantive difficulty.

## A. Pre-fix versus post-fix repository behavior

- Starting artifact: QuTiP simultaneous diagonalization before PR #2586, using
  sparse eigensolvers on highly degenerate commuting charge operators. The target
  paper cites QuTiP; this is a downstream-toolkit gap, not a target-author bug claim.
- Private artifact: fetched patch `sources/qutip_2586.patch`, commit
  e410210f1121276b66b1411afc75ccd42181ce09, 2024-12-18. It repairs degenerate
  eigenvector handling and defaults simultaneous diagonalization to dense data;
  its regression has six-qubit total occupation with seven distinct eigenvalues.
  QuTiP's official changelog independently records #2586. Also retrieved #2530
  (constant/time-dependent Bloch-Redfield dispatch) and #1965 (ODE-failure detection).
- Outcome: recover orthonormal joint gauge-sector bases and reliable downstream
  spectral propagation without treating degenerate eigenvectors as independent sectors.
- Shortcut: force every operator dense, as the small-system upstream fix permits.
- Failure regime: many commuting Gauss operators at realistic Hilbert dimensions;
  a dense fallback resolves correctness but not the memory bottleneck.
- Independent bottlenecks: degenerate joint eigenspaces; sparse symmetry-sector
  construction; propagation and observable consistency across basis changes.
- Check: upstream regression, orthogonality/commutator residuals, exact sector
  multiplicities and gauge-resolved dynamics.
- Status: concrete candidate verified during supplementary source audit; not one
  of the four fixed pilots. The original target's own public repository/fix history
  was not recovered. The archived experimental launchers' missing lattice files
  remain a separate integration limitation, not a manufactured historical fix.

## B. Original penalty versus later implementable protection

- Starting artifact: full Gauss-law penalty, no compiler for bounded local controls.
- Private artifact: single-body protection construction in arXiv:2007.00668,
  pseudogenerator construction in arXiv:2108.02203; privately verified certificates.
- Outcome: compile local errors and synthesize analog/digital protection schedules.
- Shortcut: uniform penalties or exponentially separated compliant coefficients.
- Failure regime: neutral local errors, bounded control range, digital phase aliasing.
- Independent bottlenecks: sector-transfer algebra; bounded-gap optimization;
  analog versus Floquet resonance decisions.
- Check: explicit small-Hilbert-space validation and scalable local certificates.
- Selected: c03_resonance_compiler. New task wrapper; not official upstream code.

## C. Finite-size reliability versus realistic many-body scale

- Starting artifact: dense small-cluster calibration and a factorized predictor.
- Private artifact: later spin-S thermodynamic treatment arXiv:2104.07040 and
  converged precomputed tensor-network outputs using a pinned existing engine.
- Outcome: infer coherent error parameters, then predict spatially resolved
  gauge leakage and gauge-invariant dynamics on dozens of matter/link cells.
- Shortcut: fit a universal lambda-squared/V-squared law or diagonalize a short ring.
- Failure regime: unprotected evolution, finite spatial inhomogeneity, higher spin,
  long-range connected observables; local leakage alone is insufficient.
- Independent bottlenecks: inverse calibration; scalable correlated propagation;
  gauge-resolved observables and finite-size checks.
- Check: small-cluster exact evolution, time-step/bond convergence, stored references.
- Selected: c02_multiscale_protection. Reference is a disclosed reimplementation,
  not recovered author iMPS code. No claim to reproduce infinite time with TEBD.

## D. Abelian protection versus SU(3) loop-string-hadron transfer

- Starting artifact: Abelian local charge operators and protection workflow.
- Private artifact: 2025 Communications Physics paper s42005-025-02230-x and
  author data repository mathew0036/LSH_SU3_data; code is on reasonable request.
- Outcome: protect local SU(3) constraints without confusing global charges with
  local Gauss laws, including the paper's two error models.
- Shortcut: port the Abelian single-body penalty using only global charge totals.
- Failure regime: globally neutral but locally gauge-breaking processes.
- Independent bottlenecks: LSH representation/signs; constraint reachability;
  choosing a valid protection scheme.
- Check: author trajectories and explicit constraint identities.
- Status: not selected for initial pilot; callable author implementation and fresh
  parameter reference generation are not established. Data-only availability is
  not silently promoted to a runnable reference.

## E. Ideal measurements versus real experimental discrepancy

- Starting artifact: raw double-well readout, imperfect preparations and calibration.
- Private artifact: experiment arXiv:2003.08945v2, Harvard Dataverse
  doi:10.7910/DVN/3RXD5F, published correlated-occupation results and code.
- Outcome: extract identifiable local gauge-invariant probabilities/bounds.
- Shortcut: independent-site occupation products or a single ideal sinusoid fit.
- Failure regime: correlated occupations, damping/readout offsets, inconsistent
  estimates and genuinely non-identifiable components.
- Independent bottlenecks: real signal inference; constrained correlation/measurement
  reconstruction; uncertainty/identifiability certification.
- Check: held-out experimental readouts, published results and analytic limits.
- Selected: c01_correlated_tomography. Synthetic extensions, if used, must be marked.

## F. Coherent protection versus bath-model integration

- Starting artifact: coherent Hamiltonian evolution and white-noise assumptions.
- Private artifact: frequency-resolved noise treatment arXiv:2210.06489, with
  privately precomputed validated open-system reference outputs.
- Outcome: calibrate colored noise and predict/select physically valid protection.
- Shortcut: constant-rate Lindblad noise or multiply coherent leakage by a power law.
- Failure regime: 1/f exponents, low-frequency regularization, degenerate transitions,
  different system-bath channels and finite protection choices.
- Independent bottlenecks: inverse spectrum inference; generator construction;
  protection decisions retaining intended dynamics.
- Check: analytical rate limits, trace/conservation tests and stored reference curves.
- Selected: c04_colored_noise. Formalism-derived reference, not claimed official code.

## G. Missing ablation: gauge protection versus spurious localization

- Starting artifact: apparent long-lived imbalance under a protecting potential.
- Private artifact: Stark gauge protection arXiv:2203.01338, including sector
  superposition/product-state ablations and Magnus-expansion diagnosis.
- Outcome: distinguish disorder-free localization stabilization from ordinary
  Stark localization or accidental frozen dynamics.
- Shortcut: maximize imbalance or minimize leakage alone.
- Failure regime: a control can freeze the desired dynamics while appearing protected.
- Independent bottlenecks: initial gauge-sector preparation; null/control ablations;
  mechanism identification rather than a single observable fit.
- Check: paired physical controls and both imbalance and gauge observables.
- Status: not selected; lacks retrieved author computation for fresh large-scale cases.

## H. Accuracy/performance tradeoff: high penalty and long time

- Starting artifact: ordinary ODE/Krylov integration of a stiff protected Hamiltonian.
- Private artifact: original paper's exact spectral evolution and perturbative
  renormalized dynamics; later digital finite-step analysis in arXiv:2007.00668.
- Outcome: retain both leakage accuracy and intended slow dynamics under stiffness.
- Shortcut: increase penalty indefinitely, use coarse steps, or project to a sector.
- Failure regime: digital aliases, secular parameter shifts and rare leakage signals.
- Independent bottlenecks: phase-accurate propagation; dressed observables;
  finite-step control selection.
- Check: spectral small-system references, step-convergence tests and slow observables.
- Status: incorporated as a challenge direction in c02/c03, not a fifth pilot.

## Anti-compression gate

Four pilot concepts are fixed before tournament results. C01 combines signal fitting
and correlated inverse inference; C02 combines calibration with correlated propagation
at non-dense scale; C03 combines algebraic compilation with bounded analog/digital
design; C04 combines spectrum inference with frequency-resolved open dynamics and
control selection. A generic solver being conceivable is not a reason for rejection
before a pilot. Conversely, merely requiring the same propagator on more random
matrices is not sufficient evidence for acceptance. Each pilot must document its
own operational gate and independently scored components before construction.

## Source locators

- https://arxiv.org/abs/2001.00024
- https://arxiv.org/abs/2007.00668
- https://arxiv.org/abs/2104.07040
- https://arxiv.org/abs/2108.02203
- https://arxiv.org/abs/2003.08945
- https://doi.org/10.7910/DVN/3RXD5F
- https://arxiv.org/abs/2210.06489
- https://arxiv.org/abs/2203.01338
- https://www.nature.com/articles/s42005-025-02230-x
- https://github.com/mathew0036/LSH_SU3_data
- https://github.com/qutip/qutip/pull/2586
- https://github.com/qutip/qutip/pull/2530
- https://github.com/qutip/qutip/pull/1965
- https://github.com/qutip/qutip/blob/master/doc/changelog.rst
