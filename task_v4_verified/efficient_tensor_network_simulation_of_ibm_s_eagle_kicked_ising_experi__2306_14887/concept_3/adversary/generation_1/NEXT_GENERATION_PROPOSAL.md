# Builder-only proposal — not authorized, built, or frozen

## Scientific mission

Prepare the same twelve-site GHZ+ state robustly against both the original
calibration uncertainty and **static residual Z drift**. Keep the original
12-cycle, `|+>^12` input, 24 alternating matching layers, fixed nominal
`exp(+i*pi*ZZ/4)`, two RX groups, angle bounds `[-pi,pi]`, and 0.95 fidelity
threshold. Do not increase the threshold or add unconstrained controls.

After each chronological `D_l -> K_l`, apply
`E = product_v exp(-i delta_v Z_v/2)`, including after the final kick.
Each site has an independently bounded, time-static
`delta_v in [-0.005,0.005]` radians per layer. This defines a lumped residual
precession interval per cycle, not an undocumented change to gate duration
or simultaneous driven-gate physics. Uniform, structured, and local fields
are all members of the public family.

## Candidate finite protocol

The UNFROZEN proposal at `proposed_suite.json` has 223 scenarios:

- 63 unchanged original cases, all with zero Z drift.
- 16 nominal-calibration drift cases: uniform, alternating, half-ring,
  control-group, and four localized-site patterns with both overall signs.
- 64 joint coherent stress cases: eight old common-channel corners, full
  aligned residual bond stress, four field patterns, both field signs.
- 16 concrete generation-1 counterexamples at the new bound.
- 64 joint random local-field cases, balanced between old-box boundary and
  interior samples.

Do not treat this JSON as an already frozen evaluator. Main may review the
family balance and select additional independently checked cases before
authorizing the build and fixing the generation-2 test suite. Publish the
model and ranges, not the hidden coordinates or private witness.

## Feasibility and the exposed weakness

On this exact proposal, generation 1 fails 20 cases and has minimum
0.9479270319006972. The private refocused candidate passes every case with
minimum 0.954247667090802. Independent tensor-gate checks agree. On the
larger 7,275-case validation set, its minimum is 0.9525501062305048.
This demonstrates a feasible finite-suite task, not robustness certified
throughout the continuous 27-parameter uncertainty box.

The stronger 0.01 field bound has real failures but no passing private
witness from the bounded searches so far; do not select it solely for
hardness without further feasibility work.

## Required trusted-checker changes, only after authorization

- Incorporate all 12 static Z phases after every layer using independent
  complex128 state-vector or gate contractions; no Gaussian shortcut.
- Retain strict JSON type/bounds validation, fixed operation count, no
  participant code imports, and all existing result fields.
- Assert state norm for every scenario. Assert global-X parity **only when
  all detunings are zero**; otherwise report parity solely as a diagnostic.
- Keep the GHZ+ squared-overlap objective, including its fixed relative
  phase. No final phase fit, postselection, or renormalization is allowed.
- Freeze new public assets, hidden scenarios, and checker hashes before
  the next isolated fresh attempt, without overwriting generation-1 logs.
- Keep all optimization methods, branch schedules, and private witness
  files out of the participant task and workspace.

The private mechanism and branch investigation are in `REPORT.md` and
the sidecar source files. Participant instructions should state the
physical mission and interface, not prescribe an algorithm.
