# Author handoff

The public handoff is `participant/`; the main agent owns `attempt/`. No model
attempt has been launched. Do not publish this directory or `challenge_pool/`.

From the paper output root:

```
python pilots/03_analog_memory/private/reference/build.py --split challenge
python pilots/03_analog_memory/private/reference/build.py --split holdout --fresh --replace
python pilots/03_analog_memory/private/reference/audit.py
python pilots/03_analog_memory/private/evaluator.py --submission SUBMISSION_DIRECTORY --report REPORT.json --split pilot
```

Run the evaluator in the main agent's escalated environment: it always calls the
shared bwrap helper. It has no trusted/direct-execution fallback. The defaults
are 120 CPU seconds and 1536 MiB per case, with 360 wall seconds to tolerate host
jitter. `runtime_seconds` means user+system CPU; `wall_seconds` is separate.

`build.py` defaults to 128 independent shots per case, four cases per split.
Readiness requires raw reference logical accuracy above 0.9 in EVERY case and
positive family headroom. Per-case 95% Wilson intervals accompany the raw rates.
`--replace` explicitly allows replacing a manifest. Existing holdout files are
reserved and rejected by the evaluator. Use `--fresh` for holdout only AFTER
inspecting the initial attempt; it draws a new private seed and marks the new
corpus post-attempt-fresh. There is no all-splits generator.
Old unreferenced NPZ files can remain after regeneration; only the manifest's
four cases are evaluated. No shots are selected based on decoder success.

The builder imports only inspected official MQT modules, not the stale example.
It uses the source's full-window final call and captures the complete inferred
space/time vector. Heterogeneous Gaussian calibration is rescaled to the
upstream unit-sigma API. This is an author adapter, not an upstream feature claim.
The source's `1e-15` terminal priors are not mathematically hard constraints:
larger initial generation exposed a decoded fault in an ideal interval. The
adapter therefore removes the fixed-zero terminal data/measurement columns from
the decoder, filters likelihood updates accordingly, and expands its answer
back into the official full-vector layout. It checks the complete source matrix
equation on every decode. This exact conditioning uses no hidden truth and drops
no shots. It applies identically to soft and hard-window references. The known
final syndrome is not rewarded in the history-accuracy core.

`manifest.json` records checksums, versions, source SHA, parameters, private seeds,
actual predictions, and source-native process-time measurements. It also records
the hard-window ablation, isolating the value of soft magnitudes from temporal
integration. The weak anchor is the hard final-syndrome-only decoder, not the
all-zero public starter. Scores are equal-weighted across two raw metrics and
two code families, with family-specific unclipped weak/reference normalization.

`replay_reference/` and `replay_weak/` are author-only saved-output fixtures for
testing the evaluator's exact 1 and 0 anchors through bwrap. Their execution time
is replay overhead, NOT a decoder speed benchmark; source decoder CPU times are
separately recorded in each report. `audit.py` also checks that a nontrivial
logical error can fail memory recovery despite perfect history, and that harmless
stabilizer changes are accepted. This establishes distinct metric objectives.

This is a bounded pilot, not a precise threshold study or experimental dataset.
The old 16-shot `build_pilot.log` is superseded calibration, not readiness evidence.
Use `build_ready_pilot.log`, current manifests and the isolated CLI reports.
Physical noise was reduced to obtain a genuinely strong reference without
shrinking either code family or the 544-qubit, 3/5-round lifted-product cases.
Do not generate or tune a new holdout before inspecting the initial attempt.
