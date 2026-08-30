# Generation 1 — builder handoff

This is the separate 10/12-site ratchet. Original `concept_3/participant/` and
`concept_3/evaluator/` remain untouched. Release only this generation's
`participant/` tree to participants, read-only, with an external writable
`OUTPUT_DIR`. Do not release evaluator, status, attempts, or source labels.

Targets are fixed before the next fresh attempt: charge/spin-sector RMSE
0.03/0.02 overall, 0.05/0.035 for every family; 25 seconds wall and CPU, one CPU,
2 GiB address space. The independent source residual threshold is 2e-8, well
below scientifically relevant prediction errors. These targets express absolute
accuracy in unit-hopping energies, not an assertion that any predictor can or
cannot meet them. No new-generation fresh attempt is launched by this builder.

Evaluate with `python3 evaluator/evaluate.py SUBMISSION_DIR --report REPORT_JSON`.
For serialized timing, prefix it with `python3 evaluator/serial.py` instead of
another affinity wrapper, not both. This wrapper shares the orchestrator's
existing global evaluation mutex when available; otherwise it uses a local
mutex. The evaluator itself is ROOT-relative and self-contained.

`participant/TASK.md` and the input documents specify interface, laws, targets,
read-only assets and dependencies. `participant/baseline/` is a freshly trained
kernel model using only public labels. `participant/baseline_exact/` is the
verbatim final original champion, with source and binary; its old promotion is
not a new-generation result. `evaluator/hidden/lineage.json` records its hashes.

Private evidence is in `evaluator/hidden/{generation_report,dataset_validation,
source_validation,reference_calibration}.json`, `adversary/{test_report,
isolation_audit_report,public_workflow_report}.json`, and `attempts/` baseline
reports. `evaluator/hidden/PILOT_WRAPUP.md` distinguishes the earlier snapshot's
uncontended scaling from concurrent timings and from the final engine.

`status.json` becomes ready only after the datasets, public model, independent
checks, 22 regression tests, real canary denials, small exact quality run, and
full-size native budget control are complete. `freeze_manifest.json` fixes
participant/evaluator contents; mutable runtime directories are excluded.
