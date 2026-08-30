# Deterministic weak baseline

`weak.json` is a valid, unoptimized fixture, not a claimed inversion.
It uses `p[edge]=0.03+0.08*((17*edge+11)%39)/38` and syndrome
`[1,6,11,16]`. No private search output is used. Regenerate the data with
`/usr/bin/python3 -B baseline/make_baseline.py`.

- Progress score: 0
- Certified gap: 4.84921987799 nats
- Certified opposite posterior: 0.0159341926516
- Certified syndrome probability: 1.9227012761e-06
- Passed: false

Full per-anchor values are in `metrics.json`; regenerate with
`/usr/bin/python3 -B workspace/check.py baseline/weak.json`.
