# Private concept selection

Source: arXiv:2009.03132v3, especially Sections II, III, IV, VI and Appendices A/B; official v1.0.0 archive, onebody kernels, lead boundary code, integration tests, voltage_raise.py, graphene.py and 1d_wire_low_level.py. The archive is retained next to the paper. Current official pitfalls and bound-state tutorials were inspected as corroborating engineering evidence, not substituted for the paper. No paper or private notes enter participant access.

## 1. Transient-transport release qualification (selected; archetype A)
- Central contribution/claim: propagate a many-fermion scattering ensemble through a time-dependent finite region attached to infinite reservoirs; accurate local current/density without simulating an ever-growing closed universe. The pulse/cavity and gated-graphene workflows are retained, alongside supported-model transfers.
- Artifacts: official model examples and quadrature module; a benchmark-authored NumPy/SciPy portability workspace with the same model/occupation/initialization/boundary/evolution/observable/experiment stages. Deliberately inadequate finite-reservoir release candidate, not misrepresented as an upstream bug.
- Decisions: finite equilibrium filling versus lead-resolved stationary filling; direct evolution versus stationary-background subtraction or a different open-system representation; continuum refinement versus discrete-state completeness; physical drive convention versus gauge equivalent implementation. Each has plausible alternatives and evidence from different tests; the task gives no preferred algorithm.
- Feedback: compare no-drive drift, transient convergence, local continuity and independently varied reservoir/temporal/spectral resolutions; diagnose why a superficially stable trace is not reliable, revise, rerun.
- Public evidence: full physical models, two exact microscopic tests, qualitative incident logs, convergence/invariance diagnostics without target traces.
- Families: Fabry–Perot voltage injection; interference ring with unequal reservoirs; released dark state; noncommuting spin drive; gated honeycomb cavity; dimerized gapped leads. Six rather than parameter-only variations.
- Evaluation: hidden local traces, initial-state accuracy, worst-family error, runtime/memory and rerun-supported experimental claims.
- Shortcut risk: diagonalize a long finite Hamiltonian and propagate occupied eigenvectors. This fails lead-resolved nonequilibrium preparation, may omit/incorrectly occupy isolated states, and is tested against long-time/resource requirements. A sufficiently sophisticated alternative finite embedding is valid; it is not banned.
- Why not standard implementation: no supplied integration recipe, coupled completeness/boundary/quadrature/time errors, genuinely different initial spectra and perturbations, and competing evidence that must be reconciled. Empirical screening remains decisive.

## 2. Automatic absorbing-boundary qualification across multiband leads (reserve; archetype C)
- Contribution: lead dispersion reconstruction plus reflection-controlled source/sink boundaries; claim of accurate long-time simulation with reduced lead volume.
- Artifacts: leads.py, kwantSpectrum and actual multiband lead examples.
- Decisions: crossing-aware band tracking versus subspace tracking; velocity-based buffer versus stronger absorption; static scattering calibration versus wavepacket certification.
- Loop: find resonant/slow-mode leakage, redesign boundary, replay wavepackets.
- Evidence: sampled band curves, finite-window packet losses, reflection budgets.
- Families: rank-deficient graphene lead, Rashba wire, BdG lead, oblique magnetic lead, multiple-extrema ladder.
- Objectives: worst-mode reflection, lead volume, setup cost.
- Shortcut: copying automatic_boundary; reserve only if source inspection yields a genuinely unsupported regime not already covered. More vulnerable than concept 1 to one optimization over a known absorber formula.

## 3. Fabry–Perot figure reproduction (rejected without building)
- Contribution/claim: voltage-pulse transient and successive current plateaus.
- Artifacts: supplied paper listing and official voltage examples.
- Decisions: time step, quadrature, measurement location; loop is basic convergence testing.
- Evidence: geometry and qualitative plateaus. Families would only be barrier parameter changes.
- Objectives: trace accuracy and runtime.
- Shortcut/rejection: run the official example or conventional finite-system propagation; not heterogeneous enough.

## 4. Smooth multiband dispersion reconstruction (rejected without building)
- Contribution/claim: Appendix A interpolation through band crossings, extrema needed by quadrature.
- Artifacts: kwantSpectrum.
- Decisions: overlap or derivative tracking; degeneracy tolerance; refinement; curve-error feedback.
- Families: spin-orbit, graphene, superconducting bands.
- Objectives: interpolation error and sample count.
- Shortcut/rejection: assignment plus adaptive interpolation is a standard isolated algorithm. Does not own the many-body workflow.

## 5. Graphene pulse propagation image reconstruction (rejected without building)
- Contribution/claim: real-space evolution in graphene billiard.
- Artifacts: official graphene.py and paper Section VI.
- Decisions: geometry discretization, sampling, plotting; limited feedback on density maps.
- Families: billiard shapes, dopings, contacts.
- Objectives: image fidelity and cost.
- Shortcut/rejection: clone-and-run, most variation is geometry-only; pixel agreement would replace scientific validity.

Only concept 1 is built initially. No claim of hardness is made before reference validation and fresh-agent measurement.
