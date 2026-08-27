# Author-side reproducibility

The current numeric fixtures are produced by `build_inputs.py`, then
`repair_annulus_mask.py` (which also selects the supported annular intervention).
This is deterministic CPU GPE relaxation, without external data or fitted labels.
The second command is retained to record the original vacuum-mask correction.
Version 2 uses exactly the same NPZ states and manifests as version 1.

The reference target is obtained by running solution/run.sh on hidden/manifest.json
with private/truth_config.json. The historical construction separately regenerated
the annular case after correcting its material mask; finalize_truth_index.py brings
the non-scored aggregate CSV index into agreement with those already-corrected
NPZ/JSON targets. All scored targets were correct before the reference and baseline
evaluations and both agent launches. This index update changes no scoring inputs.

`validate_reference.py` independently checks the propagator against DOP853, and
`reference_campaign.py` produces the primary, guard-ablation and timestep-halving
experiments, claims, and source-data figures. `evaluate.py` reruns the submitted
system rather than trusting its output tables, including all three public
configurations. The known-good solution's report documents the substantive
finite-system discrepancy instead of asserting a universal paper conclusion.
