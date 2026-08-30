# Source connection and authoring provenance

Seed paper: Graham R. Dennis, Joseph J. Hope, Mattias T. Johnsson, *XMDS2: Fast, scalable simulation of coupled stochastic partial differential equations*, arXiv:1204.4255v2, revised July 17, 2012; Computer Physics Communications 184 (2013), 201–208. Source: `https://arxiv.org/abs/1204.4255v2` and `https://arxiv.org/pdf/1204.4255v2`.

Official implementation: `https://github.com/GrahamDennis/xpdeint`. The main worker supplied a local source archive under the task's `authoring/sources/`; this worker read it but did not modify anything outside `concept_2`. Upstream source code was not copied into the challenge. The supplied simulator is an independently written NumPy/SciPy educational model.

The concrete source-native connection is not merely terminology:

- `xpdeint/Features/ErrorCheck.tmpl`, lines 56–90, runs full-step and half-step integrations; lines 114–123 subtract their outputs and halve the step. Lines 139–140 repeat integration steps. Source locator: `https://github.com/GrahamDennis/xpdeint/blob/master/xpdeint/Features/ErrorCheck.tmpl`.
- `admin/userdoc-source/reference_elements.rst`, line 273, describes this difference as an error **estimate**, not a proof. Its IP-operator and algorithm sections describe exact linear evolution and fixed-order Runge–Kutta integration. Public documentation: `https://xmds.sourceforge.net/reference_elements.html#error-check` and `https://xmds.sourceforge.net/faq.html#when-can-i-use-ip-operators-and-why-should-i-and-when-must-i-use-ex-operators`.
- `admin/userdoc-source/worked_examples.rst`, line 333, warns specifically that adaptive Runge–Kutta convergence for **stochastic** equations can be deceptive. `reference_elements.rst`, line 1455, explains that stochastic terms can make embedded step estimates unreliable. Public documentation: `https://xmds.sourceforge.net/worked_examples.html`. This narrower warning is not represented here as an upstream claim about deterministic NLSE integration.
- `xpdeint/Segments/Integrators/RK4Stepper.tmpl` is the source-native fixed-order integrator connection: `https://github.com/GrahamDennis/xpdeint/blob/master/xpdeint/Segments/Integrators/RK4Stepper.tmpl`.

Our Mode B hypothesis is deliberately stronger than XMDS2 documentation: that the supplied temporal certificate **together with** sampled conservation and spectral-tail checks establishes low-band density accuracy. A successful witness falsifies this finite-resolution workflow, not the convergence of RK4 or XMDS2 itself. The two-component focusing periodic Gross–Pitaevskii system is deterministic; stochastic noise is not required for this challenge.

## Why this target is nontrivial

The input has only modes |k|≤3, fixed nonzero coupling and nonlinear strength, and no user-selected grid, step count, forcing, or noise. Cubic products are exactly dealiased. The linear operator is exponentiated exactly, so the linear ablation has no temporal resonance mechanism. Scoring ignores global wavefunction phase and targets component densities at |k|≤4. A simple conservation-invariant mismatch, high-frequency initial alias, or single lucky endpoint cannot pass.

Five public parameter/shape perturbations and three late times must all have an uncertainty-subtracted density error at least 0.30, while the eight-time full-field step-halving difference is at most 1e-4 and the sampled tail mass is at most 0.02. Both coarse and fine trajectories must preserve mass to 2e-5 and energy to 2e-4. Stronger nonlinearity alone tends to violate the certificate or tail constraints; this is a constrained nonlinear witness search, not implementation of a standard solver or evaluation of a closed-form example.

The reference is validated separately by temporal refinement, spatial refinement, and a different adaptive integration method. The safety factor on numerical uncertainty is a conservative engineering rule, not an interval-arithmetic proof. Unresolved references receive zero credit. All reference decisions and uncertainties are recorded per family member.

## Privileged development, not tournament evidence

Twenty-four random/nominal calibration cases and a 160-proposal privileged local search were run before any fresh-agent trial. The inexpensive search uses a lower-fidelity reference and does not certify a hit. Authoring records and any full certification are exclusively under `adversary/`. Only `participant/` should be exposed to tested agents. No reference solution or private incumbent is needed to grade a submission. Thresholds and evaluator copies are frozen in `evaluator/hidden/freeze_manifest.json`; empirical status remains `pending_tournament`.

## Generation-three ratchet

The source-native connection is unchanged. Both generation-two fresh evaluations passed officially. V3 has the stronger minimum normalized constraint margin and supplies the baseline. Private perturbation audits select a small joint physical uncertainty with fully resolved references, not a numerical threshold increase. The final finite public family and limits are frozen before fresh trials.
