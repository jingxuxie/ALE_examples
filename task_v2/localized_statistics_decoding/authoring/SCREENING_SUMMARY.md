# Final screening disposition

Status: **rejected**. Reason: **remains_too_easy**.
Three substantive versions were built, independently reference-checked, and
screened with new ultima-alpha sessions through the requested allowlisted runner.
All old versions and exact evaluator JSON outputs are preserved. No hard
candidate is retained, and no fourth substantive version was created.

| Version | Task mode | Reference score | Fresh score | Fresh elapsed | Fresh timeout |
|---|---|---:|---:|---:|---|
| v_01 | Known-model regional posterior repair | 1.0 | 1.0 | 1125.771 s | no |
| v_02 | Syndrome-only calibration and temporal deployment | 1.0 | 1.0 | 900.742 s | no |
| v_03 | Curated quantum-decoder failure recovery | 1.0 | 1.0 | 1059.857 s | no |

The first v_01 launch failed before model initialization because the parent
sandbox mounted the Codex runtime read-only. Its exact evaluator output records
zero deliverable credit, but this is classified as an infrastructure failure,
not a hardness round. The retry used approved escalation for runtime startup
while the child retained the prescribed participant/attempt allowlist.

The v_01 and v_02 fresh solutions learned or reconstructed exact local inference
and met every held-out accuracy band. The v_03 fresh solution developed native
search and inference code, recovered 71 of 72 hidden logical sectors, produced
syndrome-consistent repairs on all 72, and stayed under every deployment limit.
It also supplied the required public predictions and diagnostic evidence.

The last task is therefore rejected under the requested score-based policy,
not retained on the grounds that its implementation or experiment history was
substantial. All three core scores were at least 0.90; none was below 0.60.

Reference validation additionally checks independent exhaustive micro-oracles,
finite-difference training gradients, the complete quantum logical/stabilizer
quotient, physical replay consistency, and acceptance of nonidentical but
logically equivalent corrections. The exact checks are preserved in authoring/.
