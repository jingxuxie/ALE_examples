# PRIVATE generation-2 staging: not installed

This tree contains a complete candidate `participant/` and `evaluator/` package.
The active generation's task, target, evaluator, and attempts are not modified.
`status.json` records frozen-target, planted, baseline, and audit evidence.

Main-session handoff, only after the current attempts finish:

1. Run the champion method over the private scale sweep independently.
2. Decide whether this fixed 8192-direction candidate is a justified ratchet.
3. Archive the active generation and install this participant/evaluator pair
   together; preserve the target, validator, and frozen manifest byte-for-byte.
4. Launch fresh isolated attempts with the unchanged one-hour budget and only
   the installed participant tree plus each empty output directory visible.

No archive, installation, target replacement, active-output inspection, or
fresh-agent launch occurs in this staging work. No hardness claim is made before
the main session's champion audit and fresh attempts.
