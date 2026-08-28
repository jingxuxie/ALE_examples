# Paper-derived hard-task tournament

**Status: in progress; no task is accepted yet.**

Target: *Atomistic spin model simulations of magnetic nanomaterials*,
arXiv:1310.6143. Authoring dates are August 27–28, 2026, with run metadata in UTC
and the working timezone America/Los_Angeles. Exactly four concepts were built.
Every initial model attempt used an isolated fresh `ultima-alpha` session,
high reasoning effort, and a 3,600-second authoring limit. None timed out.

## 1. Solution-gap mining

The review, its appendices, official VAMPIRE history/branches, issues and pull
requests, release metadata, adjacent papers, Spirit's implementation, and author
data/notebooks were inspected. No separate target-paper supplement was located.
The complete per-candidate starting artifact, private solution, outcome,
shortcut, failure regime, independent bottlenecks, and checks are recorded in
`authoring/candidate_gaps.md`. Primary-source details and bounded API snapshots
are in `authoring/source_audit/`.

| Direction | Candidate and privileged gap | Disposition |
|---|---|---|
| A: pre-/post-fix | MPI spin-accumulation overcounting; official fix `ed2f0719`, PR #99 | Mined, not separately built |
| B: adjacent improvement | Colored quantum noise plus causal spin memory; official quantum branch and later author archive | Built: `quantum_bath` |
| C: realistic scale | Irregular hierarchical dipolar fields versus point macrocells/direct tensors | Mined; field-only reduction risks one-kernel compression |
| D: physical-family transfer | Nonuniform transition saddles and fluctuation factors; native Spirit GNEB/MMF/HTST | Built: `activation` |
| E: real-data discrepancy | Ni/Gd measured magnetization/DOS versus classical predictions; later author data | Mined; not built separately from B |
| F: integration failure | Sublattice occupancy, transport, fields and atomistic derivatives; later official transport sequence | Built: `transport` |
| G: incorrect ablation | Internal-energy/coherent scaling versus constrained thermal free energy; official CMC | Built: `free_energy` |
| H: correctness/performance | Atomistic FFT boundary/self-term and precision repairs | Mined; not built separately from C |

The CMC paper predates the review: its privilege is a hidden official module,
not an incorrectly claimed later publication. The quantum implementation has
an upstream build integration problem; its reference is an independently
validated equation-level port, not a claim that the pinned branch builds
unchanged. The archive's measured Ni/Gd curves are not labels for the synthetic
transient cases. No fifth concept was introduced.

## 2. Four minimal pilots and reference checks

Each pilot starts with `participant/{TASK.md,input,workspace}`,
`private/{reference,challenge_pool,evaluator.py}`, and an empty `attempt/`.
Private auxiliary validation/provenance files do not become participant inputs.
TASK files are short missions without paper citations or expected answers.
Public examples are unlabeled; they are not a labeled training set.

| Pilot | Core outcome and scale | Per-case budget | Reference evidence |
|---|---|---|---|
| Quantum bath | Spin/memory transients and covariance; up to 46,656 spins, 1,536 steps | 180 s, 1.5 GiB | Pinned later equations; independent DOP853 errors about 2.4e-12 spin and 6.9e-12 memory; refinement and zero-temperature limits |
| Transport | Resistance, channel currents, atomic fields and tangent derivatives; up to 50,000 atoms | 20 s command / 90 s outer, 1 GiB | Official post-fix extraction; 30-case independent audit, max relative difference 5.92e-16, analytic and symmetry checks |
| Activation | Connecting index-one saddle, barrier, full tangent spectra, log harmonic entropy factor; N=6–40 initially | 90 s, 2 GiB | Native GNEB/HTST, independent Hessian/finite differences, inertia and both downhill branches |
| Thermal free energy | Direction-constrained torque and free-energy curves; 2,048-spin films and 2,744-spin particles | 600 s, 4 GiB | Official CMC, independent chains, angular refinement/symmetry and uncertainty checks |

Activation asks for the stated harmonic entropy factor, **not** a full dynamical
HTST rate. The pinned Spirit source's rotated-anisotropy Hessian indexing defect
is excluded from native-validated cases rather than treated as ground truth.
Native float32 energy-getter rounding is documented separately from accurate
independent energy differences.

Thermal references also passed an independent exact two-spin directional-measure
audit: four physical models, 33 angles, 12 chains per angle, maximum observable
discrepancy 2.79 standard errors and R-hat 1.011. Wrong-measure/bond-counting
controls disagree by over 218 standard errors. This validates the kernel and
measure, not arbitrary large-system mixing. See
`authoring/free_energy_exact_audit/STATUS.json`.

Scoring is continuous and baseline-relative, without finite-quality threshold
plateaus. Means and worst-family results are reported separately. Activation
balances search and fluctuations with a quartic aggregate; its calibrated
strong anchor is .9375 with runtime omitted, not 1.0000. The other score scales
are not numerically identical. Each pilot preserves its explicit formulas.

## 3. Initial fresh-agent tournament

| Difficulty order | Pilot | Fresh authoring minutes | Initial mean / worst family | Held-out challenge mean / worst family |
|---|---|---:|---:|---:|
| 1 | Activation | 16.71 | .937125 / .937017 | .936736 / .936475 |
| 2 | Thermal free energy | 53.49 | .983706 / .962738 | .985749 / .968700 |
| 3 | Quantum bath | 25.43 | .99999998 / .99999994 | .99999998 / .99999994 |
| 4 | Transport | 13.95 | 1.000000 / 1.000000 | 1.000000 / 1.000000 |

**All four solve their original scopes.** The ordering follows worst-family,
then mean score, but does not mistake different calibrations for evidence of
hardness. Initial and challenge case counts are respectively 6/9 quantum,
6/18 transport, 6/3 activation, and 6/12 thermal. The thermal initial figure uses
the original sequential evaluator. A concurrent isolated replay with the same
frozen per-case scorer gives .984411/.965552; the challenge uses concurrent
independent cases. Runtime-dependent sample counts make stochastic replays
differ slightly, but either run robustly solves the task. Both are retained.

Successful solutions are substantive, not grader/path workarounds:

- Quantum: batched FFT forcing, all three bath variants, adaptive eighth-order
  coupled integration and memory. Largest held-out runs take roughly 19 seconds.
  Naive whole-record FFT allocation fails the 1.5 GiB cap, but batching succeeds;
  the failed naive baseline does not prove frontier difficulty.
- Transport: one reusable, fast resolved-channel algebra implementation handles
  compensated order, empty sublattices and current/interface reversals. The
  contract does not include spin diffusion, MPI or integrated trajectories.
- Activation: invariant-plane and general-manifold searches, saddle refinement,
  spectra and connectivity. Small-case residuals are around 2e-11 meV or better.
- Thermal: a correct direction-constrained projected exchange sampler, a
  separate Jacobian-pair verification kernel, and symmetry-aware MBAR/free-energy
  reweighting. Initial evaluation takes approximately 537–538 seconds per case.

The initial anti-compression gate overestimated the significance of multiple
components: fixed composite solvers handled the frozen scopes. This empirical
correction is explicitly appended to the candidate inventory. Transport and
quantum are discarded after their entire challenge pools are solved. Activation
and thermal free energy are retained only for counterexample investigation.

## 4. Counterexamples and ratchets

### Activation: source-scale ratchet 1, fresh confirmation running

The immutable solver succeeds at N=512 in 11.25 seconds compute, with correct
saddle/spectra, but times out at N=2048 under 90 seconds. This is **not** a memory
failure and does not establish wrong physics when no answer is produced.
Native GNEB plus sparse HTST and exact structured spectra certifies the N=2048
reference in 10.24 seconds under the same resource caps. Its trusted localized
continuation seed is an author advantage, not an equal cold-start comparison.

Independent failure clusters establish more than a dense-eigensolver issue:

1. Replacing dense steps with equivalent structured linear algebra still spends
   the entire budget following highly unstable coherent candidates.
2. Unchanged 45- and 65-image localized paths omit the positive nucleation
   barrier and return no candidate **before any eigensolve**; 97 images resolve
   the boundary layer on the inspected prototype.
3. Correct localized saddles can fail the original full-chain connectivity
   relaxation budget. Longer relaxation reaches both supplied basins.

A combined diagnostic repair succeeds in about 18–20 seconds on the inspected
boundary/interface prototypes. It is not a fresh-agent result or an accepted
task solution. Evidence and caveats are preserved in
`authoring/activation_scale_probe/`.

Ratchet 1 publishes only the original successful solver as a baseline, one
unlabeled inspected long example and one short control. It keeps the same
Hamiltonian, outputs, tolerance scales and 90-second/2-GiB budget, but requires
scalable search/connectivity/fluctuations across coherent, boundary-localized
and soft-interface regimes up to N=4096. Scored cases require new parameters,
not merely renamed inspected inputs. The private exact banded evaluator passes
ten independent dense/finite-difference checks, including arbitrary rotated
nonplanar states; a full N=2048 spectrum takes about .17 seconds.

Eleven newly parameterized native references are frozen: six initial cases and
five further held-out cases, including N=3072 and N=4096. Source-native authoring
and certification of those largest cases takes 30.31 and 54.65 seconds. Maximum
saddle residual is 9.55e-12 meV; maximum native sparse log-factor discrepancy is
4.29e-8. Every selected reference has index one and two certified downhill
branches. The reference is the lowest among the native-certified mechanisms
compared, not an exhaustive global-optimality proof over arbitrary spin states.

All eleven source/scoring audits pass. Missing either search or fluctuations
scores below .70 in every tested ablation. Exact isolated strong replay scores
**.937321 mean / .937015 worst** on the initial ratchet set and
**.937446 / .937346** on the five held-out cases. On the six new initial cases,
the immutable original submission scores **.312412 / .000000**: both long-chain
families time out, while coherent controls score .937237. These are substantive
search/scalability failures, not schema, permission or build errors.

A new `ultima-alpha` session started August 28, 2026 at 03:06:03 UTC
(August 27, 20:06:03 PDT), with a 3,600-second limit, an empty attempt directory,
and no prior-attempt access beyond the intentionally published baseline source.
All case, reference, scoring and participant artifacts are frozen before launch.
Fresh confirmation scores and final disposition are pending. No acceptance
claim follows solely from the older solver's timeout.

### Thermal: rejected after physical counterexample audit

The original challenge pool is solved. Four source-grounded scouts retain the
same N=2048 Hamiltonian, directional ensemble and observables. They investigate
competing bulk/surface anisotropy, two-ion/onsite competition, and weak-interface
twists. Candidate mechanisms are extensive global-proposal rejection and
angular sampling/overlap failures, not a changed ensemble or a tighter error
threshold. A weak-interface scout has severely unconverged reference chains
(R-hat 26.55) and is rejected as an oracle, not counted against the participant.
The other reduced-grid scouts show no significant torque discrepancy (maximum
1.85 combined standard errors); their sampling and reduced-grid MBAR diagnostics
are not mislabeled as full-budget solver failures.

One compensated surface/bulk case received a full 136-job source reference
audit with independent trajectories, hot/cold starts, angular midpoint and
reflection checks. All quality gates pass: worst R-hat 1.037, split R-hat 1.040,
and the independent strong score is **.994628**. The immutable original solver
scores **.995195** in **540.54 seconds**, with 172,724 KiB measured peak RSS.
Thus the most thoroughly validated prospective counterexample is solved too.

Thermal free energy is rejected with **no ratchet and no additional model
launch**: no validated natural failure region was found. This is a bounded
counterexample search, not a proof that arbitrary anisotropy/phase regimes are
easy. Full evidence, scout limitations, reference gates and protected-file
hashes are in `authoring/free_energy_counterexamples/STATUS.json`.

## 5. Isolation, integrity, and reproducibility

`authoring/launch_round.py` invokes the supplied allowlisted runner with the
requested model and read-only participant path. Each model starts with an empty
attempt directory, no network, no private references, and no other attempt.
Deliberately published ratchet baseline code is the only allowed prior-solution
material. Prompts, model headers, start/end times, exit codes and file hashes
are recorded under `authoring/runs/`.

Evaluation adds a separate bubblewrap namespace: only the submission, current
input file, participant/runtime and output directory are mounted; network and
credentials are absent. CPU/address-space/output limits are enforced. The
isolation probe confirms private references, author source trees and auth files
are inaccessible. See `authoring/isolation_audit.json` and
`authoring/scale_audit.json`. Initial participant and submission hashes remain
unchanged after evaluation; `authoring/tournament.json` records those checks.

Numerical dependencies are pinned and supplied read-only (NumPy 1.24.4, SciPy
1.10.1, Numba .61.2), avoiding an incompatible host user-site installation.
Source native engines are private. Evaluation may need sandbox escalation to
create bubblewrap namespaces, but never falls back to an unsandboxed submission.

The complete evidence includes all four pilots, frozen references, challenge
pools, source provenance, initial attempt code/logs, score JSONs, counterexample
scouts and ratchet artifacts. An accepted production package will only be
created if a new isolated confirmation scores below .70 with a substantive
unsolved component while the strong reference exceeds .90. Otherwise the final
report will explicitly reject the paper-derived task selection.
