# Paper-gap mining report

**Decision: reject all four tested designs; no frontier-hard task is accepted.**

Audit date: August 28, 2026 (UTC). All four scored fresh `ultima-alpha`
sessions completed within their individual one-hour limits. All achieved
solved-level performance on their frozen public contracts. The two most
promising designs also survived additional private challenge evaluation.
No scientifically defensible failure region justified a ratchet. In
particular, a discovered scalar-reference discretization qualification is
not reclassified as participant failure.

This is a rejection of these four empirical designs, not a claim that the
paper or its descendants cannot yield a harder task. No fifth concept, new
physical problem, arbitrary tolerance tightening, or production task was
substituted after observing these results.

## 1. Source investigation and private gaps

The investigation included the original paper and appendices, released
checkpoints and experiment scripts, official repository history, issues and
release tags, and the authors' later compact-gauge-flow work. Exact downloads,
git histories and hashes are retained in `private/sources/` and
`private/source_manifest.json`.

- Original source: arXiv:2207.00283, including the v3 appendices; official
  `continuous-flow-lft` at `7b34521cea48f464d0790a4896b2fe86cbfedfa6`
  (August 23, 2024), original release `e33a0e5`, and parameter release
  `e6bec65`. Actual trained parameters come from Zenodo 7547918.
- Adjacent source: *Non-Perturbative Trivializing Flows*, arXiv:2410.13161,
  including its Lie-derivative and integration appendices and released
  experiment data from Zenodo 15576712.
- Later author implementation: `bijx` at
  `f476c5b4a3d51cb4b2883a17cef8bd5501f211cd` (August 23, 2026), with release
  history through v1.3.2. Relevant real changes include duration derivatives
  (`74828bc`), compact-group projection/step dispatch (`46537bc`, `73e4daa`),
  kernel resizing (`555423f`), density sign (`7dd214c`) and Fourier channel/
  momentum conventions (`7080c16`).
- Original issues did not supply an undiscovered substantial implementation
  fix; the archived issue/history audit distinguishes scientific defects,
  documentation changes and dependency compatibility changes.

The complete eight-direction inventory is `private/candidate_gaps.md`.
Each entry records its participant starting artifact, private solution,
central outcome, plausible shortcut, intended failure regime, independent
bottlenecks and verification method. These are not eight variants of one
simulator:

| Direction | Candidate gap | Private capability | Disposition |
|---|---|---|---|
| A: pre/post fix | Non-unit-time adjoints and inverse density composition | Genuine later RK4 and density fixes | Built as 01 |
| B: adjacent improvement | Independent-real Fourier representation and channel-aware spectral densities | Later Fourier metadata, bijections and tests | Built as 02 |
| C: realistic scale | Full trained scalar-flow checkpoint execution | Author analytic trace/convolution and released L64 parameters | Built as 04 |
| D: physical-family transfer | Scalar-to-U(1)/SU(2)/SU(3) transport | Later Lie derivatives, Haar divergence and group integration | Built as 03 |
| E: data discrepancy | Reliability of learned-density/importance-weight diagnostics | Released independent experiment density arrays | Unbuilt: available diagnostics do not by themselves identify missing support |
| F: component integration | Sampler, inverse flow, density and gradient conventions | Later distribution/sampler composition and fixes | Integrated into 01 |
| G: ablation correctness | Transfer kernels with an incorrect resize origin | Actual resize fix and checkpoint/orbit geometry | Integrated into 04 |
| H: accuracy/cost | Exact density and sensitivity instead of noisy/dense derivatives | Original analytic scalar trace and later Lie derivatives | Independent pressure in 02–04 |

No hidden trained gauge network is claimed. Pilot03's loop-potential adapter
is newly authored, restricted to an explicitly specified invariant-potential
family; its reference executes the released author's differentiation and
integrator primitives. This distinction lowers its priority relative to a
fully preserved pre/post trained-model deployment gap. Its complete
provenance is in `pilots/03_gauge_transport/private/PROVENANCE.md`.

## 2. Four minimal pilots and anti-compression screen

All four were built before production selection. Each has the requested
`participant/{TASK.md,input,workspace}`, `private/{reference,challenge_pool,
evaluator.py}` and `attempt/` structure. Public missions are short, do not
name the paper, and provide no expected-output training set. Detailed input
contracts specify observable mathematics rather than fixed-source patches.
The participant never receives the later solution-bearing source/history.

| Pilot | Independently checked components | Scale and representation |
|---|---|---|
| 01 adjoint composition | Primal, endpoint-time/parameter/input gradients, absolute density, inverse, acceptance trace | Authentic pre-fix modules; small 3–6-dimensional compositions; 96/384 requested steps |
| 02 Fourier transport | Packing, unrelated-coordinate decoding, symmetry, transport, density, sensitivity, momenta | Mixed-parity 2D/3D geometries, batch/channel layouts, up to 128×128 |
| 03 gauge transport | Lie vector, Haar divergence, transported state/density, weight/initial gradients | U(1), SU(2), SU(3), forward/reverse; 16×16 and rectangular lattices |
| 04 scalar checkpoints | Field, exact trace, coupling derivatives, transferred kernel, forward/reverse transport | Actual L32/L64 checkpoints; 50/300-feature models; conditional and odd/even transfer profiles |

The pre-build anti-compression question was asked explicitly. A black-box ODE
call alone does not reconstruct the independent representation, density,
geometry and parameter-contraction components. Nevertheless, this argument
was treated only as a reason to test, not proof of hardness. In particular,
pilot01 does **not** enforce the long-trajectory adjoint-memory bottleneck:
its small empirical instance permits direct sensitivities. It is not evidence
that a generic method fails at realistic adjoint-memory scale.

## 3. Fresh-agent tournament

Every scored attempt uses the supplied `run_allowlisted_codex.sh`, model
`ultima-alpha`, effort `xhigh`, ephemeral context, a read-only participant
tree, its own initially empty writable output directory, and a 3,600-second
cap. Evaluators run submitted code in fresh bwrap namespaces with only public
files, that submission and current-case I/O mounted; no private answers,
pool siblings, previous attempts or network are available.

There were four earlier author-interrupted prefix launches. Their initial
stdin-header diagnosis was wrong: logs later showed model activity. These
prefixes are excluded, retained in full, and are not counted as failures.
Output directories were verified empty before the scored restarts. Exact
details, including the pre-launch TASK-only edit in pilot01, are in
`private/LAUNCH_AUDIT.md`. There were no score-driven restarts.

### Initial results

| Pilot | Fresh duration | Mean core | Worst scored family | Outcome |
|---|---:|---:|---:|---|
| 01 adjoint composition | 3,128 s | 0.999999999 | 0.999999997 | Solved |
| 02 Fourier transport | 869 s | 0.949999970 | 0.949999917 | Solved; exact-output anchor is 0.95 |
| 03 gauge transport | 1,232 s | 0.998037578 | 0.993425059 | Solved |
| 04 scalar checkpoints | 1,467 s | 0.996979968 | 0.996323512 | Solved against frozen 100-step references |

Fourier's normalized skill is 0.999999879: its 0.95 raw score is not a 5%
accuracy deficit. To choose two additional searches without mistaking score
calibration for difficulty, the initial worst-family ordering uses the
exact-output score ceiling (0.95 for Fourier, 1 for the other scoring
functions). The resulting order, hardest first, is **03, 04, 02, 01**.
The deeper searches therefore focus on 03 and 04 despite their already solved
scores. Their attempted solutions have no missing core output branch.

### Private challenge and stress results

| Pilot/pool | Cases | Mean core | Worst family |
|---|---:|---:|---:|
| 01 disjoint challenge | 5 | 0.999999998 | 0.999999996 |
| 02 mixed-geometry hidden pool (initial evaluation) | 11 | 0.949999970 | 0.949999917 |
| 03 near-center challenge | 6 | 0.992419855 | 0.968834300 |
| 03 additional structured stress | 3 | 0.989370064 | 0.968828424 |
| 04 conditional/transfer challenge | 8 | 0.991159334 | 0.986328110 |

Full per-family and per-case results, rather than just averages, are in
`private/tournament.json` and each pilot's `private/*_report.json`.
Scalar figures here measure the frozen reference-execution contract; the
continuous-IVP qualification in Section 6 is essential.

## 4. Shortcuts actually discovered

1. **Adjoint composition:** the submission uses analytic affine/Fourier
   branches and SciPy DOP853 with variational/adjoint machinery for nonlinear
   branches. It replaces rather than repairs the historical custom adjoint.
   Every tested density and sensitivity family is correct. This bypass is
   allowed by the public contract and decisively defeats the proposed task.
2. **Fourier representation:** one NumPy FFT/index-mask implementation handles
   all tested parity, dimensionality, channel and phase families. Analytic
   determinant multiplicities and derivatives complete the solution. This is
   empirical evidence of compression to a reusable representation algorithm,
   not merely a prediction that FFTs should work.
3. **Gauge extension:** a U(1) angle branch and a matrix-group branch supply
   loop-local derivatives and Haar divergence. An ordinary high-accuracy
   DOP853 solve plus continuous adjoint then handles every tested transport
   family. The reference's specialized CG3 stepper is not necessary at this
   task's tested accuracy/scale once the geometric derivatives are correct.
4. **Checkpoint execution:** FFT convolution, orbit expansion, precontracted
   time/coupling features, analytic trace and a batched 100-step RK4 path solve
   all released-model branches. Reconstructing these components took work,
   but none remained unsolved in the one-hour test. Faithful replication of
   the publicly disclosed 100-step reference is also a discretization shortcut.

No claims about training quality, ESS, phase coverage or physical-observable
bias are inferred from these deterministic execution scores.

## 5. Realistic-scale and baseline measurements

- **Gauge:** a dense all-coordinate Lie-Hessian baseline on 16×16 SU(3)
  took 110.96 s and peaked at 8,296,480 KiB resident memory. Sixteen exponential
  Euler steps gave state/density normalized errors 0.02164/0.07780; its
  six-component score, with absent sensitivities scored zero, was 0.11919.
  This is a measured weak direct baseline, not proof against every optimized
  autodiff method. The fresh solver's maximum initial-case time was 50.64 s,
  with 352,636 KiB peak RSS; challenge/stress peaks stayed below 370,000 KiB.
- **Scalar:** the dense starter scores 0.24619. Native instantaneous L32/L64
  probes complete in 2.87/7.24 s; native forward/reverse solves time out at
  approximately 69–155 s. Conditional/transfer branches are unimplemented,
  so those failures are not misreported as performance failures. The fresh
  solver completes initial cases in at most 4.65 s and challenges in at most
  3.37 s. Its numerical probe accuracies exceed 0.999999999 in aggregate;
  smooth runtime factors explain the remaining frozen-reference score loss.
- **Fourier:** the independently implemented magnitude-only/rFFT-storage
  shortcut scores 0.10, with no execution failures, in isolated evaluation.
  The deliberately unimplemented public stub has a separate failed smoke
  report and is not this numerical baseline. The fresh solution's slowest
  case is 6.07 s, comfortably within the 60-second cap.
- **Adjoint:** actual pre-fix modules are the weak anchor, not fabricated zero
  outputs. The entire submitted standard/challenge requests take 2.05/2.70 s.
  These small instances cannot establish a meaningful memory advantage for
  the source's custom adjoint.

All timing is machine-local CPU timing. Scalar/Fourier/adjoint evaluation is
limited to four cores; gauge evaluation uses an eight-core allocation.
No GPU speed claim is made. Runtime and memory are distinguished from numerical
quality; unmeasured RSS is not silently reported as zero.

Scoring remains continuous: adjoint uses rational error scores calibrated
against actual pre/post modules; Fourier uses a smooth log-error calibration
with weak/strong anchors 0.10/0.95; gauge uses
`1/(1+9*sqrt(RMS_error/RMS_identity_error))`; scalar uses rational relative
error quality times `1/(1+.03*T/Tref)`. Scalar reports additionally retain
unclipped empirical weak-to-strong normalization. A fast correct solver can
exceed the measured strong runtime anchor; this does not mean accuracy >100%.

## 6. Reference checks and scientific qualifications

- **Adjoint:** the actual fixed reference scores 0.999999705 and 0.999999557
  on standard/challenge pools against refined stored outputs. Independent
  analytic error is 3.25e-14 or less; inverse directional finite differences
  disagree by at most 3.16e-11. Private source extraction and compatibility
  changes are recorded, rather than passing off a reconstructed fix as a
  historical checkout.
- **Fourier:** official modules, not a copied proposed algorithm, generate
  answers. Independent index enumeration, arbitrary-coordinate decoding,
  small dense real determinants/adjoints and finite differences validate the
  representation and derivative conventions. Actual official CLI score is
  0.95, with all eleven cases executed. That privileged source run is not
  represented as an isolation test.
- **Gauge:** stored answers use 256 upstream CG3 steps; 512-step refinement
  scores 0.99816455 initially and 0.99289866 on the near-center challenge.
  Minimum individual reference component quality is 0.92681752. Explicit
  every-link/every-generator small-case divergence agrees to 1.47e-16.
  Group residuals are around 1e-14. The stationary stress case also has an
  independently integrated analytic density, with relative discrepancy
  9.06e-10 and minimum refinement component quality 0.99974674.
- **Scalar:** actual author execution in the same isolated runtime scores
  0.970873786 on both pools, with exact agreement to stored 100-step answers;
  this is not answer replay. Independent instantaneous dense/finite-difference
  and symmetry checks pass. However, the stricter 100-versus-200-step
  refinement assertion **failed**. That failure is preserved in
  `pilots/04_scalar_checkpoint/private/reference/refinement_validation.log`.
  The further 100/200/400-step audit is stored separately in
  `pilots/04_scalar_checkpoint/private/reference/refinement_audit.json` and
  its `refined/` outputs; it does not overwrite the frozen oracle or scores.

Across all ten scalar transport inputs, 100-versus-400-step mean output
quality is 0.96482473, with a minimum of 0.83904877 on conditional forward L64.
For 200-versus-400 steps, mean/minimum improve to 0.99802920/0.99107039 under
the same metric. All ten refinements finish; seven are computed serially and
three on separate four-core allocations. No integration arithmetic or frozen
public file changes. The serial interruption used to parallelize author-only
work is recorded in `reference/refinement_audit_execution.json` within pilot04.

The scalar public specification simultaneously declares the continuous IVP
as target and discloses a fixed 100-step reference. It is therefore not valid
to interpret a later refined-reference discrepancy as an unsuspected hard
participant requirement. For example, native forward L64 has 100-versus-400
field quality 0.89912932 under the original smooth metric, improving to
0.99346961 for 200-versus-400. The reference is not exact merely because its
instantaneous divergence is exact. The audit and its interpretation are
retained in `pilots/04_scalar_checkpoint/private/continuous_gap_audit.md`.
This qualification independently prevents promoting pilot04 as a validated
continuous-flow frontier task. No retrospective score or threshold change
is used to rescue it.

The **unchanged** submitted scalar solver was then independently re-executed
in isolation against the 400-step stored oracle, using the original error
metric and original timing denominators. These are explicitly diagnostic
rechecks, not fresh attempts or revised tournament grades:

| Refined-oracle diagnostic | Mean core | Worst family | Execution failures |
|---|---:|---:|---:|
| Initial pool | 0.988417802 | 0.953741096 | 0 |
| Challenge pool | 0.983412617 | 0.929460412 | 0 |

The minimum individual output accuracy remains 0.83904877, reported rather
than hidden, on the conditional forward L64 field. The 100-step oracle has
essentially that same discrepancy. No central family falls below 0.90, and
the hardness decision does not change even under this finer independent
reference. Reports are `pilots/04_scalar_checkpoint/private/refined_test_report.json`
and `pilots/04_scalar_checkpoint/private/refined_challenge_report.json`.

## 7. Counterexample search, ratchets and confirmation

**Gauge search.** The original challenge changes Haar-random links to valid
near-center configurations. Additional probes apply gauge conjugation to
near-center U(1)/SU(3) cases and test exact identity SU(3), where the drift is
zero but Haar divergence and density change are not. These target distinct
real errors: tangent/measure confusion, loss of covariance, group constraints,
and confusing a stationary field with a zero log-density derivative. The
reference is independently validated in that region. The submission passes
all fifteen initial/challenge/stress cases; worst component aggregate in the
stress pool is 0.97360158. No root-cause cluster of substantive failure exists.

**Scalar search.** The eight challenge cases cover conditional interpolation
midpoints/endpoints, row-aligned couplings, displacement-resolved and odd/even
transfer geometry, and forward/reverse transports at published sizes. The
submission solves all branches. The deeper integration audit finds a
reference-fidelity qualification, not evidence that the fresh solver cannot
perform the stated computation. Uniform refinement of an already fast RK4
implementation is not established as a frontier bottleneck. There is no
evidence-backed reason to add arbitrary large-field or high-coupling cases.

**Failure classification.** Tested dense baselines have genuine cost and
missing-branch limitations; fresh submissions do not. Gauge residual
discrepancies are compatible with numerical reference refinement. Scalar's
discretization ambiguity is author-side. Namespace/path and interrupted-launch
issues are explicitly separated from scientific scores. No clerical failure
is credited as hardness.

**Ratchets: zero. Confirmation fresh agents: zero.** Both deeper searches
are rejected at the natural-counterexample gate. There is no ratcheted task
to put before a second fresh model, and no fresh held-out ratchet distribution
is claimed. Running a confirmation of an invented tighter-tolerance task
would violate the requested gate rather than satisfy it. The extra structured
gauge cases are counterexample probes, not a hidden ratchet.

## 8. Acceptance decision and artifact index

None satisfies the conjunction of a valid reference, a complete public
contract, fresh mean core below 0.70, and a substantively unsolved central
technical component. All frozen-contract mean scores exceed 0.90; no severe
hidden-family failure is averaged away. Pilot04 additionally requires an
unambiguous continuous-target oracle before any future reuse for IVP claims.

- `selection.json`: machine-readable rejection, rank, gate decisions and
  ratchet/confirmation counts.
- `private/tournament.json`: measured aggregate/family scores and durations.
- `private/candidate_gaps.md`, `private/history_audit.md`: eight directions,
  exact starting/private artifacts, historical caveats and verification logic.
- `private/source_manifest.json`, `private/public_artifact_audit.json`,
  `private/final_audit.json`: source pins, public hashes and final consistency
  checks.
- `private/LAUNCH_AUDIT.md`: excluded prefixes and isolation/restart disclosure.
- `pilots/01_adjoint_composition/` through `pilots/04_scalar_checkpoint/`:
  frozen public missions, code/data, private references, generators, evaluators,
  logs and actual submitted solutions.

There is intentionally no accepted production `participant/` tree at the
output root. Releasing any of these solved pilots as frontier-hard would
contradict the empirical results.
