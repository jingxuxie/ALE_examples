# Private audit

This directory holds task-builder baseline measurements, identifiability diagnostics, frozen target commitments, and evaluator selftest logs. No fresh agent was launched by the builder. None of these files may be mounted into a strategy sandbox. The suite is balanced across public physical regimes and is not selected using fresh-agent failures.

`baseline_hidden.json` is the final startup-aware, 32/32-valid reference measurement. `development_baseline.json` predates target calibration and records provisional thresholds; its raw error measurements are retained for provenance, not as the final pass condition. `target_commitment.json` is the authoritative final timing/source/target freeze. The empirical hardness decision remains pending the main session's fresh-agent tournament.
