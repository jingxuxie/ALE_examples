# Concept 3: hidden-spin material response

The participant mission is `participant/TASK.md`; detailed schemas are in
`participant/SCHEMA.md`. This folder implements the requested 96-spin latent
temperature/field-response variant, not the earlier planar-defect proposal.

Mount ONLY `participant/` read-only for a tested participant, with separate work
and output directories. Do not expose this package root, `evaluator/`, `tests/`,
`adversary/`, the authoring script, or surrounding paper-task directories.

Organizer scoring:

`python -I evaluator/evaluate.py --submission OUTPUT_DIRECTORY --output SCORE_JSON`

Only `predictions.npz` is read; submitted code is never imported or executed.
See `evaluator/README.md` and `adversary/FREEZE.json`. No agents are launched.
