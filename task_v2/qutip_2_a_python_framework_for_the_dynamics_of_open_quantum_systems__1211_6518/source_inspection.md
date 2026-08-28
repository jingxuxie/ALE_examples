# Private source inspection and concept selection

Paper: J. R. Johansson, P. D. Nation, F. Nori, arXiv:1211.6518.
Retrieved 2026-08-27 from https://arxiv.org/pdf/1211.6518.
Official release archive: https://github.com/qutip/qutip/tree/qutip-2.2.0.
The paper describes 2.1; 2.2 is the earliest non-platform-specific Git tag
available in the official repository. This is not described as a pre-fix 2.1 checkout.

Inspected artifacts: floquet.py, bloch_redfield.py, examples/
ex_floquet_markov_master_equation.py, ex_floquet_quasienergies.py,
ex_brme_coupled_qubits.py, ex_compare_td_formats_II.py, ex_qpt_gates.py;
the official Floquet, master-equation, and superoperator test locations.
No separate experimental dataset is associated with these numerical examples.

Central contribution: arbitrary time-dependent Hamiltonian/collapse-operator
evolution, Floquet and Bloch--Redfield solvers, with integrated process diagnostics.
Central empirical claim: driven and coupled systems can have substantially
different dissipation under microscopic spectral-bath models than under local
Lindblad approximations; efficient solver implementations make comparative
numerical studies practical. Sections 4.2--4.5 and figures 1--4 are the anchors.

Important limitations visible in the source: period-table lookup and fixed
harmonic cutoffs; a population-oriented Floquet RWA; basis conversions at API
boundaries; a constant output-time increment in the old Redfield evolution loop;
assumptions about independent coupling operators; operator amplitudes versus
rates in time-dependent callbacks. These are not merely installation problems.
The pilot is an explicitly benchmark-authored NumPy/SciPy migration workspace,
not a claim that all its defects occur in the historical release. It retains the
connected experiment/solver/analysis workflow rather than porting Python-2/Cython
installation issues. The paper and full solved historical source stay private.

## Five candidates, assessed before construction

1. **Release qualification of a spectral-bath dynamics service (A).**
   Contributions/claim: all three dynamics branches and discrepancy analysis.
   Assets: reconstructed multi-file migration of the official driven-qubit,
   coupled-qubit, oscillator, and noisy-gate experiments.
   Decisions: local versus spectral dissipation (invariants alone do not settle
   this); population rates versus coherences at degenerate transitions; direct
   integration versus period reduction or sparse action; convergence versus
   runtime, supported by refinement and frame-equivalence experiments.
   Loop: reproduce approximate baseline, inspect residuals and basis/thermal
   diagnostics, repair, rerun controlled comparisons and scaling.
   Public evidence: six unlabeled manifests, microscopic conventions, invariants,
   a tiny analytic limit, runnable baseline, and two selectable configurations.
   Hidden: driven broadband spin; driven filtered multilevel ladder; common-bath
   dark-state manifold; nonsecular coupled spins; pulsed thermal oscillator;
   noisy two-qubit process channel. These are six changes of physics/noise or
   computational regime, not seeds or dimensions alone.
   Evaluation: continuous full-state/channel error, worst-family performance,
   runtime/memory, independently regenerated experiment evidence.
   Shortcut risk: one generic Lindblad solver handles the two explicit-collapse
   branches but does not infer spectral sidebands or Redfield cross terms.
   A coherent solver suite remains necessary; empirical screen will decide.
   SELECTED FOR PILOT, conditional on reference and fresh-agent results.

2. **Robust noisy-gate pulse redesign (B).**
   Contributions/claim: time-dependent evolution and process tomography.
   Assets: official iSWAP example; public gate/noise configurations.
   Decisions: pulse family, robust objective, truncation; optimize/inspect/rerun.
   Hidden: detuning, thermal baths, correlated noise; fidelity/runtime/leakage.
   Shortcut: GRAPE plus autodifferentiation and a generic optimizer is a convincing
   route for the small systems in the paper. Scaling it just adds optimization
   workload, not a defensible paper-central frontier challenge. REJECTED.

3. **Floquet quasienergy tracking across avoided crossings (B).**
   Contributions/claim: Floquet mode computation and figure 1.
   Assets: official amplitude-sweep script; mode overlap and unitary diagnostics.
   Decisions: phase gauge, tracking rule, step adaptation; refine/compare loop.
   Hidden: qubit, ladder, coupled spins; tracking error/runtime/continuity.
   Shortcut: one-period propagator plus assignment/SVD handles all families.
   The work is a standard numerical algorithm implementation. REJECTED.

4. **Monte Carlo event statistics and resource qualification (A).**
   Contributions/claim: time-dependent collapse operators and efficient solvers.
   Assets: official time-dependent-format and trajectory tests.
   Decisions: event localization, estimator, variance allocation; run/CI/refine.
   Hidden: decay, thermal jumps, driven cavity; error/calibration/runtime.
   Shortcut: standard norm-threshold quantum jumps with adaptive ODE integration
   and independent random streams solve the supplied-family structure. REJECTED.

5. **Infer bath spectra from process-tomography measurements (D).**
   Contributions/claim: process diagnostics and spectral bath dependence.
   Assets: would have to synthesize observations; no real measurement dataset.
   Decisions: model family, experimental design, regularization; fit/residual/refit.
   Hidden: colored, thermal, correlated environments; prediction/calibration/cost.
   Shortcut: small nonlinear least squares with a forward solver. It also replaces
   the actual paper workflow with convenient synthetic inference. REJECTED.

Only concept 1 merits construction. If it fails the standard-shortcut screen,
the other four do not become stronger by renaming them as concept 2.
