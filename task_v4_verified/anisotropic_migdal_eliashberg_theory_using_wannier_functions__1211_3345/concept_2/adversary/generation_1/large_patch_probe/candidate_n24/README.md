# Private 24-patch planted constraint instance

This is a private design artifact, not a promoted participant package. `input/` contains only the public constraint data. `witness.npz` and all audits are private and must not enter a participant mount.

Three different eight-patch feasible source pairs form contiguous, labeled bands; none is copied three times. Within-band matrices scale by N/8 to retain moderate integrated couplings under weights 1/N. Each band has its own common coupling rescaling and mode-dependent shared perturbations. Positive, reciprocal, nonuniform interband matrices connect every band, and the mode matrices do not commute. No label permutation conceals the structure.

The same row/diagonal/full-static invariants hold between both endpoints and the supplied reference. The source low-Tc alignment is a private design choice, not a participant absolute-temperature target. The only success target is the robust ratio **1.11**, frozen from private evidence before replay. The exact artifact checker gives **1.1219300515770714**; baseline is admissible with score **1.0**, not valid. The full signed-frequency audit is independently assembled for all three energy families, and the regular-row control passes.

`provenance.json` records source identities, scales, integrated row bounds, noncommuting-mode diagnostics, target rule, and generation CPU. `evaluation.json` and `evaluation_audit.json` are outputs of the complete pure-artifact evaluator, including archive/link guards, reasons, and resource summaries. `baseline_evaluation.json` records the baseline. The frozen checker is `evaluator/evaluate.py`; it loads only its own `hidden/frozen_input` and never candidate code.

`../adapter/dimension_and_path.diff` documents all changes to the actual fresh search: only public path, patch count, edge count, reshaping, and equality row scaling. Reversing those substitutions reproduces every original source byte. Its n=8 control reproduces the original champion exactly. No search tolerance, iteration count, restart count, seed, objective, or solver is changed. This is a larger genuine search domain, not a shape/path failure test.

The actual larger replay and its final qualification are in `../replay_summary.json` when complete. A bounded or incomplete replay must not be described as a proved optimization gap or one-hour resource failure. Likewise, a private passing witness alone does not establish hardness; the visible weak-band structure may admit a simple decomposed search.
