# Artifact-only evaluation

Run `python evaluator/evaluate.py --artifact witness.npz --output result.json --audit-output audit.json` from the concept directory. A positional artifact path and `--result` alias are also supported. The checker reads only the NPZ artifact and private frozen inputs/code; it never imports participant workspace code or runs candidate code. `_physics.py` is the frozen public implementation, with its input default redirected to `hidden/frozen_input`. `hidden/frozen_manifest.json` records the frozen hashes. Parent infrastructure must protect the evaluator directory, but candidate edits to their public workspace cannot alter scoring.

The result separates `admissible`, `target_met`, and `valid`. `valid` requires the target, refinement convergence, and both independent controls. Failure and baseline results still get audit JSON files. Successful score computation does not by itself certify validity. Scores use unrounded temperatures and the worst published family/grid ratio.

`_audit.py` independently assembles the full signed-frequency dense operator. Its normal-state self-energy uses a direct signed sum plus the exact omitted Einstein tail, rather than the public cumulative-sum implementation. A regular-row control compares two distinct regular graph kernels against the isotropic problem. These are numerical consistency checks, not interval proofs of infinite-cutoff errors or material realizability.

Private generation scripts, search logs, the fixed-instance provenance, and the curator witness live in `hidden`. Do not expose that directory, `attempts`, or `status.json` to participants. No fresh tournament runner is invoked by this package.
