# c04_colored_noise

Release **only** `participant/`. Implement its root `solver.py`; `workspace/` is
scratch. `attempt/` is strictly empty and reserved for the main tournament.
The full scientific contract is `participant/input/protocol.md`.

Private reference: `private/reference/solver.py` plus `engine.py`. This is a new
benchmark-author implementation of the explicit secular formalism, **not official
paper code**. Dimension 64; inference, degenerate rates, and budgeted decisions are
separately scored. There are 9 screening, 6 challenge, and 3 reserved confirmation
cases, with precomputed outputs. No participant agents or Codex runs are launched.

From this directory:

```
python private/reference/checks.py
python private/reference/precompute.py
python private/evaluator.py --submission private/reference --participant participant --split screening --output private/validation/reference_screening.json
python private/evaluator.py --submission private/weak_baseline --participant participant --split screening --output private/validation/weak_screening.json
python private/reference/precompute.py --freeze-only
```

The evaluator always delegates to task-root `authoring/isolated_eval.py`; it does
not import submissions or fall back to trusted execution. It supports
`--split screening|challenge|confirmation` and `--participant DIR` override.
Reports include `mean_core`, `worst_family`, `family_scores`, `component_scores`,
and `cases`. `private/validation/` distinguishes author precompute from isolated
runs. See `PROVENANCE.md` for source attribution and scientific caveats.

**Minimal-ready:** actual isolated screening reference mean/worst 1.000/1.000;
weak 0.574067/0.572201. Reference worker runtime mean/max 1.078/1.522 seconds.
22 independent analytical/invariant checks pass. Full measurements, limitations,
challenge regions, and pre-freeze repairs: `private/validation/REPORT.md`.
