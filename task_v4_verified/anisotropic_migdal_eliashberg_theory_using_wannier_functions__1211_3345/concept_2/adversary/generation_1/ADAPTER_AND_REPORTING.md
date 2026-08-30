# Pending generation 1: private evidence only

The best unrounded fresh score selects v2. Its advantage over v1 is at floating-point roundoff scale, not evidence of materially better optimization. `champions/generation_1` preserves the exact frozen submission, original evaluation JSON, audit, launch manifests, and selection manifest. `archived_originals` preserves the active participant and evaluator without numerical or reporting edits.

`replay_champion.py` runs the actual archived search, not its old witness on new constraints. The only source edit replaces the hardcoded `PARTICIPANT` path by `/participant`; a recorded diff and AST comparison enforce that restriction. Search parameters reproduce the documented M=48, 24-restart run, followed by its recorded M=192, zero-restart refinement. Both artifacts are audited and the better score is credited, favoring the champion. Inputs are mounted read-only and each fresh search output directory starts without any witness. Bubblewrap exposes system runtime libraries, that instance's public participant assets, and the output directory only; no private witnesses or other sidecar inputs are visible.

The original instance is an obligatory replay control. Execution, path, resource, or inadmissibility failures do not establish a genuine optimization gap. Only an admissible failing result against an independently passing private witness can support the ratchet, and the numerical gap must be assessed for significance before proposing a target. A private local maximum alone is not a global-optimum certificate.

## Reporting-only improvement

`reporting.py` adds `reason` on every outcome, `core_score`, `worst_family_score`, their explicit common definition, and resource measurements. Both score summaries intentionally equal the minimum ordered ratio across the configured families/refinements. It leaves the original `score` and `valid` untouched and asserts this invariant. Existing archived evaluation JSON and numerical contracts remain unchanged. Evaluator timings exclude search; search timings and peak RSS are measured separately using GNU time. Linux peak-RSS units are KiB.

Any eventual pending evaluator must use this reporting contract, but no new participant/evaluator numerical contract is promoted or launched by these scripts. The parent alone reviews and launches a ratchet.
