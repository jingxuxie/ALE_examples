# Deterministic baseline audit

The public fixture uses p[edge]=0.03+0.08*((17*edge+11)%39)/38 and
syndrome [1,6,11,16]. It is not derived from any optimized private artifact.
`participant/baseline/make_baseline.py` reconstructs it without a search.

Structural validity: true. Passed: false. Core score: 0.
Certified gap: 4.84921987799355; opposite posterior:
0.0159341926515715; syndrome probability:
1.92270127610116e-06.

The full independent result is `baseline_independent_metrics.json`; the
public frontier result is `participant/baseline/metrics.json`. The oracle
audit compares all 21 anchors. This is a format/calculation starting point,
not a warm-start optimizer or a near-target witness.
