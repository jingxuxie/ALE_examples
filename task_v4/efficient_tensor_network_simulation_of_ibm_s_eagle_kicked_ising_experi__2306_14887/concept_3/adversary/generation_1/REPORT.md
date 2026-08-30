# Generation 1 privileged adversarial report

## Outcome

The fresh champion is a valid solution of the original frozen task. No
failure inside the original calibration model was found. Its exact fresh
files are archived, unchanged, in `champions/generation_1/`; all 25 files
match `attempts/frozen_v_1/` byte for byte. No private builder source or
witness was added to that archive. Champion pulse SHA-256:
`d96fc70c75500849200c31c19adfe1870b643a4a855684060a6eb92b61160df6`.

There is a scientifically meaningful **proposed extension** that defeats
this champion while retaining a privately established achievable 0.95
target: bounded static single-site Z drift after each physical layer.
This is NOT a retroactive failure of generation 1.

## Original model: independent check, not duplicate sweeping

The fresh solver already reported 41,039 scenarios, including all 32,768
old-box vertices, and 128 continuous local adversarial optimizations.
Rather than repeat that full sweep, this sidecar evaluates 1,064 cases
with a newly compiled 4,096-amplitude simulator: 32 prior worst points,
eight common-channel corners, and 1,024 newly seeded interior/near-boundary
points. Minimum: **0.9590763502134589**; failures below 0.95: **zero**.
The twelve lowest cases agree with the unchanged trusted checker.
This is numerical evidence, not a continuum certificate.

See `old_box_report.json`, `old_box_cases.npz`, and `archive_manifest.json`.

## Proposed physical extension and confirmed failures

After every original layer `K_l D_l`, apply a fixed-duration residual drift:

```
E(delta) = product_v exp(-i delta_v Z_v/2)
|psi> = E K_23 D_23 ... E K_0 D_0 |+>^12
```

Each `delta_v` is static throughout all 24 layers. The original kick and
bond calibration coordinates retain exactly their published ranges. The
new field is an explicit extra physical uncertainty, not an old admissible
parameter. It can model a residual local frequency offset during a fixed
idle interval per cycle; it does not claim to model detuning continuously
through the finite-duration gates. Angles are dimensionless radians per
site per layer. Bounds 0.005 and 0.01 correspond to about 0.286 and 0.573
degrees per layer, respectively; no hardware-specific gate time is assumed.

| Field / calibration | Drift magnitude | Independently confirmed fidelity |
|---|---:|---:|
| Uniform, nominal old calibration | 0.005 | 0.9877146293 |
| Uniform, prior old worst calibration | 0.005 | 0.9484480954 |
| Strongest selected joint boundary case | 0.005 | **0.9479270319** |
| Uniform, prior old worst calibration | 0.01 | 0.9171373769 |
| Half-ring signs, prior old worst | 0.01 | 0.9298095217 |
| Control-group signs, prior old worst | 0.01 | 0.9399730117 |
| Alternating signs, prior old worst | 0.01 | 0.9507127663 |
| One drifting site, prior old worst | 0.01 | 0.9570943732 |
| Strongest searched joint boundary case | 0.01 | **0.9111829992** |

Search coverage includes 1,560 structured cases at six amplitudes and
5,888 boundary/interior cases at 0.01. The latter include **all 4,096 local
Z-sign patterns** at the old worst calibration, 768 coherent fields with
random old-box vertices, 512 joint random vertices, and 512 joint interior
points. Of the 4,096 local-Z sign cases, 4,094 fail 0.95 at this calibration.
Rescaling the 256 lowest 0.01 cases to 0.005 yields 40 failures, minimum
0.9479270319; this rescaled subset is not claimed exhaustive at 0.005.

Standalone counterexamples are in `cases/`, including `strongest_0005.json`
and `strongest_001.json`. Every case explicitly records that nonzero Z
drift lies outside the ORIGINAL model. Reproduce from the concept root:

```bash
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1 python adversary/generation_1/reproduce.py --case adversary/generation_1/cases/strongest_0005.json
```

## Root-cause clusters

1. **Collective coherent drift interacts with calibration errors.** A
   uniform 0.005 drift alone passes comfortably at nominal calibration,
   but the same field combined with old-box boundary calibration fails.
   Spatially coherent fields are much more damaging than a single-site
   field. The effect is not an artifact-format or numerical loophole.
2. **Both leakage and phase error matter.** For uniform 0.01 drift at the
   old worst point, cat-basis population is 0.92617409, relative cat phase
   is 0.19730 radians, and negative global-X parity population is 0.043171.
   Since cat-basis population is already below 0.95, even an ideal final
   relative-phase correction alone cannot repair this case.
3. **Nonuniform coherent fields can cause almost pure leakage.** The
   half-ring case has cat-basis population 0.92981206 and only -0.00305
   radians relative phase. This motivates genuine preparation-time
   refocusing across spatial profiles, not a final phase fit.
4. **The old symmetry/solver assumptions no longer apply.** Nonzero Z
   drift breaks global-X parity and invalidates the old parity-preserving
   Gaussian propagation shortcut. Only zero-drift cases should assert
   global-X parity; all cases should still assert norm and finite fidelity.

The new C++ full-state kernel was checked against an independent tensor-gate
extension of the trusted primitive gates: maximum discrepancy 7.44e-15;
finite-difference pulse-gradient discrepancy 7.26e-10. The independent
extension does not assert parity for nonzero drift. No original checker
source or scenario was modified.

## Private feasibility, including the branch suggestion

At drift bound **0.005**, a private continuous refocusing optimization
uses 34 training scenarios, 120 iterations / 135 evaluations, and 130.44
seconds. It starts from a private builder witness, not from code injected
into the fresh archive. Training minimum: 0.9553549181.

The saved candidate passes **7,275** further case evaluations:

| Validation family | Cases | Minimum fidelity |
|---|---:|---:|
| Original frozen suite, zero drift | 63 | 0.9579151825 |
| Independent old-box check | 1,064 | 0.9615523361 |
| Structured fields at 0.005 | 260 | 0.9586312481 |
| Broad joint boundary/interior fields at 0.005 | 5,888 | **0.9525501062** |

The four lowest cases in each family are independently confirmed. Counts
are case evaluations, not a claim of 7,275 distinct or untrained points.
The record is `drift_0005_broad_validation.json`; the actual private witness
is `drift_0005_validated_candidate.json` (SHA-256
`8169c81d11b8cd23f1b37a895f89b0002dcf223338508eb60419df2bafc65744`).

The stronger **0.01** bound is not established feasible by this bounded
search. A 260-iteration continuous run reaches 0.9328409179 on its training
set. A separate screen of 208 simultaneous-pi branch schedules verifies
nominal invariance within 6.22e-15, but the best schedule reaches only
0.9263559915 on 270 validation cases; subsequent continuous refinement
reaches 0.9313229693 on 34 training cases. Calibration gain errors make the
branches non-free in the robust objective. These are search outcomes, not
impossibility proofs. Branch code and diagnosis remain private and are
not written into participant material.

## Focused next generation

Recommend the **0.005** static-Z bound, retaining the same graph, input,
target, 24 layers, fixed ZZ gates, bounded two-group angles, old calibration
ranges, and **0.95** threshold. A natural, unfrozen 223-case proposal is
already independently checked: fresh champion minimum 0.9479270319
(20 failures); private refocused witness minimum **0.9542476671** (no
failures). See `NEXT_GENERATION_PROPOSAL.md`, `proposed_suite.json`, and
`proposed_suite_validation.json`.

This sidecar did not change `participant/`, `evaluator/`, original frozen
scenes, `freeze_manifest.json`, or `status.json`, and did not launch any
agent. Writes are confined to `champions/generation_1/` and
`adversary/generation_1/`. Integrity verification is recorded separately.
