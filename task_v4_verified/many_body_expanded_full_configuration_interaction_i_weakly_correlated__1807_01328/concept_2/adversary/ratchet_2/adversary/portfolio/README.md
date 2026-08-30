# B3 bounded private achievability portfolio

This directory is privileged generation evidence only. It is not participant
input and must not be exposed to a fresh solver. All writes stay in this directory.
The actual fresh B3 output is neither read nor scored here. No fresh agents are
launched and no frozen package files are changed.

`budget.json` records a conservative 720-second execution budget plus a
180-second startup/handoff reserve within the requested 15-minute cap. Setup,
gradient checks, optimization, selection, official scoring, and saved reporting
share that execution budget. Optimization stops early to reserve 150 seconds
for scoring and reporting. The timestamp-bound search is not intended to be
restarted without a separately authorized budget.

`engine.py` adapts the earlier private affine paired-sector engine to independently
perturbed pair energies, OV/OO transfers, and fixed density interactions. The
adjustable center remains the original 42 VV controls. `engine_checks.json`
compares full-noise energies and increments with the public model and checks
analytic derivatives away from the box-truncation distribution's kinks.

`search.py` performs bounded least-squares searches from the privately archived B2
champion and earlier portfolio endpoint. Training seeds are `303171000` plus the
run index. Each seed spawns separate VV and full streams. A separate private
selection pool uses seed `303170021` with 32 cases per family. Neither pool uses
the frozen official directions. Exact run schedules and counts are saved.

Every endpoint is a legitimate static witness-schema artifact, though it need not
meet the numerical target. Selection is committed in `preheldout_selection.json`
before running the unchanged official evaluator on `best_witness.json`. The
selected candidate is not refitted after official scoring. Its exact report is
`official_report.json`; `summary.json` records results, budgets, and freeze hashes.

The warm-start artifacts had already been scored privately during packet
construction. This search does not query those reports during training;
"preheldout" refers to this portfolio's new official call, not historical
blindness to the reference artifacts' earlier outcomes.

If the saved artifact officially passes nominally and reaches 122/128 in BOTH
families, the remaining budget is used for up to 128 additional independently
drawn full-noise cases with seed `303179991`, verified by the frozen independent
verifier. Partial completion must not be represented as a completed holdout.

To reproduce the static official score from this directory:

    python -B ../../evaluator/evaluate.py best_witness.json --report repeated_report.json </dev/null

Unsuccessful bounded searches leave feasibility unknown. They do not establish
mathematical impossibility, and no reference solution is required.
