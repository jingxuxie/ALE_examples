# Author handoff

Export `../participant/` only. Submit root `solver.py`, with
`solve(case: dict) -> dict`. `../attempt/` is empty and reserved for main's fresh
participant. No fresh Codex pilot was run during authoring.

Frozen splits: 9 screening, 12 challenge, 6 reserved confirmation cases; three
families; lengths 32–160. Confirmation seed: 210802203. `manifest.json` records
case/reference hashes, seeds, and separate analog/digital anchors. Do not refreeze
after participant runs. `reference/solver.py` and `weak_reference/solver.py`
are standalone frozen answer readers, not participant starters.

From the pilot root:

```
python private/evaluator.py --submission attempt --participant participant --split screening --output result.json
python -m unittest discover -s private -p test_physics.py -v
```

The evaluator uses the common task-root `authoring/isolated_eval.py` exclusively,
never imports submissions, and propagates isolation-infrastructure exceptions.
Nested-sandbox bwrap validation requires host/escalated execution. The optional
`--participant` supports ratchet mounts. Limits: 60 seconds and 6 GiB per case.
Summary fields: `mean_core`, `worst_family`, `family_scores`, `component_scores`,
and `cases`. Author results live under `reference/validation/`.

Independent tests build dense tensor-product operators in a separately rotated
basis and enumerate all 256 Hilbert states on four-site rings. Across all three
families and target variants they compare reachable sector/penalty rows, analog
and circular uncertainty gaps, Hermiticity, destructive interference, boundaries,
and a digital alias. Other checks distinguish Z2 G from W and ensure submitted
certificates cannot influence robustness scores.

Calibrated reference: 0.9663825298; weak: 0.1357208808. The weak submission has
perfect privileged certificates to isolate synthesis. Scores are calibration,
not evidence of optimality or hardness. Raw margins and isolated reports are
retained. Every strong schedule has a positive worst-case local margin; weak
schedules retain exact local resonances.

This synthetic author reimplementation is not an official bug-fix. It certifies
direct local departures and a diagonal digital protection layer, not high-order
errors, all-sector compliance, or full interacting Floquet dynamics. U1 protection
is single-body; Z2 pseudogenerator protection is not. Published patterns initialize
the search; repeating finite patterns does not imply global compliance. Generic
optimization may solve this benchmark: retention requires main's empirical fresh
pilot. See PROVENANCE.md and ANTI_COMPRESSION.md, written before construction.
