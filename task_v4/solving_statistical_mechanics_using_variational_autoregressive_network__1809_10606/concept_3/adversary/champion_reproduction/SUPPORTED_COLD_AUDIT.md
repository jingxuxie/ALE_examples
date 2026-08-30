# Follow-on supported-interface REPLAY audit

The user accepted the source-faithful replay's numerical reproducibility with an explicit original-query max-TV difference of 0.0002738557673308919. No bitwise-original champion claim is made, and no recovered science code was edited.

The subsequent bounded audit is documented in `../champion1_cold_stress/REPORT.md`. It uses a preregistered deterministic subset of 1,200 saved posterior draws, not the full 9,600-draw replay. Earlier supported stress60 passes (mean KL 0.00376711, max TV 0.08268756). New cold48 fails (mean KL 0.02529506, worst-family mean KL 0.04273012, max TV 0.40005286). Frozen weakfit independently fails the cold maximum-TV gate at 0.20509031.

The query JSON, exact true probability arrays, both frozen predictors, approximation diagnostics, commands and source hashes are preserved in that sidecar. All audited fields are zero or readout-local; nonlocal interface cases are excluded, not counted as failures. Finite-observation sensitivity is suggested, not established as irreducible; full-posterior and original-champion cold scores remain unknown.
