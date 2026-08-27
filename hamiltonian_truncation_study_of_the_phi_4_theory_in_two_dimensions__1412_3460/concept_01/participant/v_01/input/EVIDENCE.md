# Numerical evidence format

Spectrum tables have columns:

`row_id,case,family,method,cutoff,sector,level,energy,gap,dimension,elapsed_s`.

Scaling rows have:

`case,method,cutoff,dimension,elapsed_s,peak_rss_mb`.

The high-water memory can be the process high-water mark, rather than a
misleading sum of per-matrix array sizes. State this in the report if used.

The `claims.json` object has a `claims` list. Each entry has `id`, `statement`,
`kind`, `rows`, `quantity`, `value` and `conclusion`. The supported quantitative
claim kind is `cutoff_drift_ratio`: `rows` contains four spectrum row IDs
`[production_low, production_high, ablation_low, ablation_high]`, all for the
same case/sector/level at the two corresponding cutoffs. `quantity` is
`energy` or `gap`. `value` is

    abs(production_high - production_low) /
        max(abs(ablation_high - ablation_low), 1e-12).

`conclusion` is `improved` if this value is below 1, otherwise `not_improved`.
Do not claim accuracy solely from this ratio. Include at least one such claim
per branch, discuss whether it supports the broader conclusion in the report,
and include any limitations or contradictory observations. Additional claim
types may be recorded in an `additional_discussion` field; they must not be
presented as independently verified measurements.

`figures/source.csv` has columns `figure,row_id,x_quantity,y_quantity,x,y`.
The row IDs point to spectrum rows, and `x_quantity` / `y_quantity` name the
columns plotted. Source rows must match those table values. These data make
the figures reproducible without an image-similarity test.
