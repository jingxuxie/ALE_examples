# Bounded late-time probe: commitments before execution

This is an author-only counterexample probe, not a new concept or ratchet. Only
this directory and `pilots/c04_colored_noise/private/reference/longtime/` may be
written. Original participant, attempt sources, evaluator, and frozen pools remain
unchanged. No new participant agents will be launched.

Two cases are fixed before running the submitted solver:

| Case | Base screening case | T | beta | amplitude | cutoff | floor | eta |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| weak_pink_T1000 | 1b74c29e8a9a | 1000 | 1 | 0.000025 | 0.45 | 0 | 0.45 |
| weak_brown_T10000 | c2ec672ca1ab | 10000 | 2 | 0.000015 | 0.45 | 0 | 0.65 |

Retain dimension 64, seven equally spaced samples starting at zero, all actions,
budget, Hamiltonian coefficients, initial state, and independent audit bath from
the base case. Set lambda=sqrt(2.6/T) and kappa=0 to isolate coherent drift from
known actuator detuning. Generate finite-band calibration from the stated weak
bath using fixed Gaussian draws, relative sigma 0.8% (positive minimum 1e-11),
seeds 48001 and 48002. All public parameter bounds remain respected. In particular,
amplitude never goes below 1e-5 and no Tmax is specified by the public contract.

Source basis: arXiv:2001.00024 Fig. 3 and energy-protection discussion distinguish
small gauge leakage from observable drift near V/lambda^2; its methods paragraph
also explicitly motivates direct exponentiation for extremely long times.
arXiv:2210.06489 Appendix B Eqs. B1--B4 provide the secular structure and protected
early incoherent scaling gamma*t/V^beta. These are regime guides, not claims of
exact scaling in this modified pilot. Both full PDFs were checked:
`https://arxiv.org/pdf/2001.00024`, `https://arxiv.org/pdf/2210.06489` (12 pages).

Reference: retain the frozen engine's exact generator, use its nonzero connected
components, and remove scalar Bohr phases before dense block expm. Independently
compare to Hermitian dissipator diagonalization plus commuting Hamiltonian phases.
Check all sampled density matrices, [D,C] for C=-i[Hs,.], discarded-entry norm
(must be zero), several original short cases, and short versions of both probes.

Run the byte-identical completed submission via the common isolated run_solver
with timeout=60 and memory_gib=6, using a copy staged here so its source directory
is not written. Monitor only the probe process's descendants through /proc for
CPU evidence, particularly on timeout. Also run the accelerated reference through
the common runner. No time limit changes or altered submission algorithms.

Scoring completeness: no late-time weak baseline is assumed or fabricated. Use
the public component formulas with their positive anchor floors against the
independently cross-checked reference. This is a conservative score lower bound
for any legally weak-anchored normalization, not a new official pool score.
A protocol timeout scores zero regardless of anchors; successful outputs retain
raw errors. If both late cases are solved, reject the proposed lead. If reference
validation fails, do not claim a counterexample.

Fairness update requested by main after inputs/reference were fixed: final runs
use `run_solver(..., timeout=60, memory_gib=6, startup_grace=30)`, strict worker
wall alarm 60 seconds, CPU soft/hard limits 61/62 seconds, and parent watchdog
90 seconds only to absorb namespace startup. Earlier startup-inclusive runs are
retained at `runs/` as preliminary evidence. Only `runs/strict_worker60_grace30/`
is used for the final disposition; no case or submitted-code change accompanies
this rerun.
