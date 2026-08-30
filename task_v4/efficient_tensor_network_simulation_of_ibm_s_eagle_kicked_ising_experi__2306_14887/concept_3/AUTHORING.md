# Privileged generation-1 ratchet handoff

## Current contract and honest status

The current task adds static local Z precession of **+/-0.01 radians per
site per layer** after every RX matching layer, including the last. All
other controls, the 12-cycle, `|+>^12` input, old calibration ranges, 24-layer
depth, and fidelity threshold **0.95** are unchanged. There are 223 hidden
scenarios and 31 public examples. Global-X parity is an invariant only in
the 63 zero-drift scenarios.

This strength is an explicitly authorized **hard_open_candidate** with
**solvability UNKNOWN** unless current-suite grading finds a passing
artifact. The private +/-0.005 drift witness is not a proof at +/-0.01.
The sidecar's smaller-bound recommendation is historical evidence, not the
current contract. Do not relabel a below-threshold private candidate as a
passing witness or claim that failure of bounded search proves impossibility.

## Isolated launch boundary

Expose only `participant/` and a fresh `attempts/v_2/` working directory to
the next tested agent. Stage actual isolated copies; do not merely instruct
an agent to ignore readable private paths. `participant/` contains exactly
`TASK.md`, `input/`, `workspace/`, and `baseline/`.

The only public pulse artifact is the original independently authored weak
nominal baseline. Its bytes are unchanged. No prior fresh submission,
prior fresh solver source, prior optimized checkpoint, private refocused
witness, or private optimization/branch diagnosis is participant material.
Do not mount `champions/`, `adversary/`, `generations/`, old attempts or logs,
`evaluator/`, builder reports, status, or freeze manifests into the fresh
agent environment. Main owns the actual allowlisted v2 launch, logging,
and final empirical status; this builder does not launch a tested agent.

## Archives and first-tournament preservation

`generations/generation_0/` is an exact pre-change archive of participant,
evaluator, status, freeze manifest, and builder documents. Its
`archive_manifest.json` verifies all archived bytes.

`champions/generation_1/` is the exact original fresh winner previously
promoted by main's request; that directory name is the historical champion
label, NOT evidence of a pass on this stronger ratchet. The original frozen
winner's first-tournament score remains `attempts/v_1_score.json` unchanged.

Raw `attempts/v_1/`, `attempts/frozen_v_1/`, and `attempts/v_1.log` have been
quarantined under `adversary/generation_1/tournament_0_raw/`. Their exact
relocation map is in `adversary/generation_1/ratchet_build/raw_attempt_relocations.json`.
Score/metadata records retain their bytes; records inside moved raw trees
remain available at the corresponding private archived paths. Never expose
them as a next-generation baseline or warm start.

## Trusted evaluation and audit

Run `python evaluator/evaluate.py --submission DIRECTORY --output JSONPATH`
from the unchanged trusted package. It reads only `pulses.json`, never imports
participant/submission code, and authenticates its hidden scenario bytes.
All valid and invalid results include the required score/resource/runtime/
reason fields. Nonzero-drift parity is diagnostic, never an invariant.

`adversary/generation_1/ratchet_build/audit_ratchet.py` compares public
vectorized evolution, independent trusted tensor contractions, and the
separately compiled full-state kernel, including independent dense RX/RZ/ZZ
gates and the unchanged zero-drift dynamics. It also checks malformed JSON,
required CLI fields, standalone public baseline execution, and private-file
leakage. `grade_candidates.py` records current-suite scores without changing
any first-tournament score.

The current freeze manifest covers public contract/assets and the trusted
checker/scenarios. Verify with `python adversary/verify_freeze.py` before
and after trusted evaluation. Do not regenerate scenarios or change bounds,
thresholds, or assets once main starts v2. No further private optimization
is needed for launch readiness at this authorized open-candidate strength.
