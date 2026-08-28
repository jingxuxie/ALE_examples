# Bounded weak spin-one transfer probe

This sidecar owns only this directory. No original pool, public input, attempt,
engine, evaluator, or initial evaluation is changed or rerun. No agents or
ratchet directories are created. Completed submission files are copied byte for
byte into an isolated sidecar snapshot; shared-runner scratch writes therefore
cannot modify the original attempt.

## Precommitted physical cases

Reuse `private/reference/build.py:make_case(18334, "inhomogeneous_weak", 0)`:
the existing L=32 weak/full-protection seed, including its exact calibration,
private true parameters, spatial profile, couplings, and correlation pairs.
Change only the prediction spin to S=1 and requested times, with two strengths:

* `weak_spin1_V0p5_L32_T8`: V=0.5; times 0, .2, .7, 1.5, 3, 4.5, 6, 8.
* `weak_spin1_V1_L32_T10`: V=1; same times plus 10.

These lie inside the original contract: L=24–64, S=1/2 or 1, V=0–12, T≤10.
The open-boundary initial state, Hamiltonian, error channels, and normalization
are unchanged. This crosses the original weak/inhomogeneous spin-half family
with its spin-one representation, rather than inventing new noise or masks.

## Source and limitations

Van Damme et al., arXiv:2104.07040, Sec. II Eqs. (1)–(3), Sec. III A/Fig. 2,
studies the spin-S quantum-link Hamiltonian with unassisted pair/link errors,
including S=1 and weak protection V/J=1. Appendix A3 emphasizes bond/time-step
convergence and the finite reliable time window of MPS predictions. The paper
does not certify this inhomogeneous finite-chain wrapper or these labels.
Increased entanglement/cost in this crossed regime is a hypothesis, not an
assumed counterexample; larger spin need not increase gauge violation.

References use the existing fourth-order `charge_engine.predict`, conserving
Q=sum_j (-1)^j n_j. Begin at dt=.1, chi=96, cutoff=1e-9 versus dt=.05, chi=192,
cutoff=1e-12. Refine only if necessary. Accept a reference only when the existing
max-difference/weak-scale normalized geometric convergence diagnostic is at
least .97. This is a numerical diagnostic, NOT a rigorous exact-solution bound.
The existing tiny explicit spin-one charge-engine check is reused, not rerun.

Only accepted labels reach submission evaluation. The unchanged solver runs
through `isolated_eval.run_solver` with 3600 worker seconds, 6 GiB, and 30 seconds
of namespace startup grace, on one CPU. Preserve the full raw execution and all
predictions; score through the existing `evaluator.score_result`. No public
contract violation or unconverged reference counts as a solver failure.

`probe.py` freezes inputs/snapshot/hashes, runs one reference level, assesses
convergence, or evaluates one accepted case. All generated files stay here.
