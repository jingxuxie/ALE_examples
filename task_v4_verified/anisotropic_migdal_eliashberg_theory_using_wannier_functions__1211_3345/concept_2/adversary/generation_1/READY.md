# Ready for parent review; not promoted

**Hardness warning:** a new two-parameter interpolation search passes at 1.094290457685765 in 8.62 CPU seconds. The n=8 draft is validated but not recommended as a hard ratchet; see `DECISION.md` and the separate `large_patch_probe/` follow-up before promoting anything.

- Pending public package: `participant/`; trusted checker: `evaluator/evaluate.py`; compatibility format: `input/FORMAT.md`.
- Frozen target: **1.09**, selected using private evidence before replay; same n=8, three-mode row/diagonal/static constraints.
- Baseline: admissible, score **1.0**, not valid.
- Private witness: **1.094955838159416**, valid, saved with independent signed-frequency and regular-row audits in `evaluator/hidden/`.
- Actual champion over every family, including cross-combination of every produced endpoint: **1.0877026333364312**, admissible and independently audited, not valid.
- Exact package validation and hostile-artifact probes: `validation/summary.json`; additional all-family M=384 private check: `validation/extended_refinement.json`.
- `DECISION.md` states the scientific interpretation, empirical gap, unchanged original contracts, reporting-only regression, and risk of an easy minimax-aware fresh solution.
- Active `concept_2/participant`, `evaluator`, and `status.json` are unchanged. No fresh launch or promotion occurred. Parent alone decides whether to promote this proposal.
