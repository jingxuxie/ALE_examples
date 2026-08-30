# Actual-champion baseline audit

The source is ../../champions/generation_1/witness.json, selected from both
completed and independently passing generation-one attempts. Byte identity
is checked in audit.py. The privileged known witness is not the baseline.

Generation-one nominal score: 1.00892989981203.
Generation-two score: 0.939363803021116; valid=true, passed=false.
Local bounds: {"certified_gap": 0.7984592325679484, "certified_opposite_posterior": 0.8376567091563732, "certified_syndrome_probability": 1.7847396190542623e-05}.
Actual anchor clusters: {"gap": 1, "none": 40, "opposite_posterior": 3}.

Thus actual gap and posterior violations, not only certificate slack,
motivate the new domain. Full public and independent metrics are retained.
