# Exact artifact and physics specification

## Static JSON

The only permitted top-level keys are `schema_version` and `a`. The version must
be the integer token 1. The array must contain exactly 4096 integer tokens from
0, 1, 2, with the published counts. Booleans, floating-point tokens, strings,
duplicate or extra keys, nonfinite constants, and trailing non-JSON data fail.
Maximum artifact size is 131072 bytes, including whitespace. The file must be
a regular nonsymlink file named `design.json`; a submission-directory symlink
also fails. Other files are ignored. Submitted Python or other code is never run.

The JSON schema records the structural/count requirements; `check.py` additionally
enforces token types, duplicate-key rejection, the byte limit, cyclic spacing,
and exact autocorrelation. A schema library alone is not the complete checker.

## Constraints and comparison

Every occupied slot must have an empty predecessor and successor modulo 4096.
Counts are 3328/512/256, giving integer sum 1024 and sum of squares 1536.
The target publishes all 4096 lags, including 0 and 2048. The authoritative
calculation accumulates integer products, without FFT rounding or tolerances.
An exact full-domain match is necessary and sufficient after structural checks;
no particular planted sequence or orientation is required.

`core_score` is 1 only for an exact valid witness. The four half-open lag families
are `[0,1024)`, `[1024,2048)`, `[2048,3072)`, `[3072,4096)`; each scores 1 only
when all its lags match. `worst_family_score` is their minimum. Squared error,
L1 error, matched-lag count, and EEC L1 error are diagnostics, not partial credit.

`runtime_seconds` measures trusted artifact checking, not solver construction.
`runtime_score` and `resource_score` are 1 for a valid bounded artifact and 0
otherwise; they cannot compensate for core failure. Solver time is not inferred
from JSON. The external attempt budget remains 3600 seconds. Ordinary rejection
returns a JSON report with exit status zero; configuration/CLI errors return nonzero.

## Full-event normalization

For total energy one, the ordered-pair EEC definition retains self-pairs, as in
arXiv:1801.03219 equations (1)–(2). The full integer direction sequence repeats
`a` twice. Its cyclic pair-product numerators are `2*c[lag % 4096]`, with common
denominator `2048**2 = 4194304`. Their sum is exactly that denominator.

Angular bin `bin` represents angle `2*pi*bin/8192`, from zero through pi.
Interior bins combine two opposite directed separations; the endpoints do not.
Each endpoint numerator is `2*c[0] = 3072`, so each endpoint has mass `3/4096`.
All interior numerators are `4*c[bin % 4096]` over the same denominator.
These are atomic masses, not densities per unit angle. Self-pairs, antipodal
pairs, the half-period lag, and the entire domain are retained.

Masslessness and antipodal momentum cancellation are exact symbolic properties
of the prescribed directions. Floating trigonometry is unnecessary for grading.
The submitted object is a physically kinematic discrete event, not a claim about
perturbative multiplicity or the analytic continuum NLO spectrum.
