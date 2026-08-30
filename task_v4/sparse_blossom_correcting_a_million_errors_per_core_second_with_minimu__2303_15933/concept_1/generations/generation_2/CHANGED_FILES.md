# Changed paths

All task assets are new under `concept_1/generations/generation_2/`:

- `participant/TASK.md`, `participant/input/{API.md,SCIENCE.md,models.py,worker.py,run_public.py,target.json}`
- `participant/input/{cases/,calibration/,runtime/,runtime_versions.json,requirements.lock}`
- `participant/baseline/{submission.py,decoder.cpp,decoder.so,Makefile,README.md}` and `participant/workspace/submission.py`
- `evaluator/{evaluate.py,qualify.py,probe_runtime.py,test_evaluator.py,validate.py}`
- `evaluator/hidden/{build_data.py,freeze.py,seeds.json,challenge/,holdout/,frozen.json,frozen.sha256,evidence/,scientific_selection.json,baseline_provenance.json,baseline_qualification.json,runtime_probe.json,sampling_report.json}`
- `attempts/` raw build, baseline, test and validation reports; `adversary/` isolated validation probes; `champions/` reserved for main.
- `status.json`, `BUILD_AUDIT.md`, and this change inventory.

Supporting stress, knob, compiler, temperature and fallback controls were added only under `concept_1/adversary/stress_harness/`. No original participant/evaluator/frozen/champion artifact or other concept was modified. The runtime and native binaries are copied assets; source edits use apply_patch.
