from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import time

from common import ROOT, SIDE


GENERATION = ROOT / "generations/generation_2"


def add_text(path, text):
    if path.exists():
        raise RuntimeError("Refusing to overwrite an audit file")
    patch = "*** Begin Patch\n*** Add File: " + str(path) + "\n" + "".join("+" + line + "\n" for line in text.splitlines()) + "*** End Patch\n"
    subprocess.run(["apply_patch", patch], check=True)


def main():
    environment = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", OPENBLAS_NUM_THREADS="1", OMP_NUM_THREADS="1")
    deadline = time.monotonic() + 1800
    while True:
        try:
            qualification = json.loads((GENERATION / "evaluator/hidden/baseline_qualification.json").read_text())
            if len(qualification["reports"]) == 2:
                break
        except (FileNotFoundError, json.JSONDecodeError, KeyError):
            pass
        if time.monotonic() >= deadline:
            raise RuntimeError("Bounded qualification wait expired; do not mark READY")
        time.sleep(2)
    if not qualification["valid"]:
        raise RuntimeError("Full-suite baseline qualification failed")
    with (GENERATION / "attempts/freeze.log").open("w") as stream:
        subprocess.run(["/usr/bin/python3", str(GENERATION / "evaluator/hidden/freeze.py")], stdout=stream, stderr=subprocess.STDOUT, env=environment, check=True)
    print("FROZEN", flush=True)
    with (GENERATION / "attempts/unit_tests.log").open("w") as unit_log, (GENERATION / "attempts/validation.log").open("w") as validation_log:
        unit = subprocess.Popen(["/usr/bin/python3", str(GENERATION / "evaluator/test_evaluator.py")], stdout=unit_log, stderr=subprocess.STDOUT, env=environment)
        validation = subprocess.Popen(["/usr/bin/python3", str(GENERATION / "evaluator/validate.py")], stdout=validation_log, stderr=subprocess.STDOUT, env=environment)
        unit_code = unit.wait()
        validation_code = validation.wait()
    if unit_code or validation_code:
        raise RuntimeError("Final tests failed; inspect immutable freeze and raw reports, do not mark READY")
    specification = importlib.util.spec_from_file_location("generation_two_evaluator", GENERATION / "evaluator/evaluate.py")
    evaluator = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(evaluator)
    frozen = evaluator.verify_freeze()
    original = json.loads((ROOT / "evaluator/hidden/frozen.json").read_text())
    for artifact in original["artifacts"]:
        if hashlib.sha256((ROOT / artifact["path"]).read_bytes()).hexdigest() != artifact["sha256"]:
            raise RuntimeError("Original frozen artifact changed")
    provenance = json.loads((GENERATION / "evaluator/hidden/baseline_provenance.json").read_text())
    for name, digest in provenance["files"].items():
        if hashlib.sha256((ROOT / "champions/generation_1" / name).read_bytes()).hexdigest() != digest:
            raise RuntimeError("Original champion changed")
    baseline = json.loads((GENERATION / "attempts/baseline_isolated.json").read_text())
    validation = json.loads((GENERATION / "attempts/validation_summary.json").read_text())
    if not baseline["valid"] or baseline["passed"] or baseline["core_score"] != 0 or not validation["all_passed"]:
        raise RuntimeError("Baseline or isolation verification is inconsistent")
    digest = hashlib.sha256((GENERATION / "evaluator/hidden/frozen.json").read_bytes()).hexdigest()
    probe = json.loads((GENERATION / "evaluator/hidden/runtime_probe.json").read_text())
    audit = f"""# Generation two build audit

Status: READY for main review and a fresh one-hour run. No fresh runner was launched by the builder.
This is ratchet 1 of at most 3. The original generation remains frozen and unchanged.

## Frozen objective and baseline

- Promoted generation_1 Python/C++ code, Makefile and native binary are byte-identical in `participant/baseline/`.
- 20% fewer pooled joint-logical failures; 15% fewer on independent holdout; no family failure-count increase; paired absolute 95% lower endpoint above zero.
- 3,072 hidden shots, six known cases, three families. Public calibration has 1,536 independent labeled shots.
- Baseline: {baseline['pooled']['candidate_failures']}/3072 failures. Challenge 212; holdout 215. Family counts: spatial pairs 108, known nonuniform crosstalk 113, space-time pair memory 206.
- The old two-pass correlated PyMatching decoder has 1,292 failures on these same hidden draws; it is not the new scoring baseline.
- Full-suite qualification CPU: {', '.join(str(entry['execution']['cpu_seconds']) for entry in qualification['reports'])} seconds. Frozen reference is the maximum, {frozen['limits']['baseline_cpu_seconds']} seconds.
- Frozen CPU cap: **{frozen['limits']['cpu_seconds']} seconds**, computed as ceil(1.25 times that reference). One process/thread; 6 GiB address space; 900 s wall watchdog. Fresh coding time remains one hour.
- Final evaluator baseline CPU: {baseline['execution']['cpu_seconds']} seconds; core/worst-family scores 0; resource score {baseline['resource_score']}; valid FAIL, not INVALID.
- Freeze SHA-256: `{digest}`. `participant/input/target.json` matches `evaluator/hidden/frozen.json` and is checked by the evaluator.

## Scientific selection and controls

33 private stress regimes were screened. Only the corrected C-contiguous, reference-verified screen (37 failures/1,056 shots) is included as evidence. The earlier invalid output-buffer run is explicitly excluded.

The chosen independent confirmation has 101 champion failures/768 shots. Quadrupling ensembles reduces this to 95 at 4.65 times CPU; on the smaller pilot it reduces 58 to 45 at 4.93 times CPU. This discrepancy and the paired uncertainty are retained, not hidden.

At 1.25 times CPU, optimistic case-wise label-oracle parameter choices remove only 3.96% on confirmation (5.17% on pilot). Compiler-only changes remove none. Eight likelihood-temperature choices remove at most 1.98% uniformly; their optimistic case-wise label oracle removes 6.93%. A low-confidence fallback to correlated matching gives no uniform confirmation improvement and at best two failures saved with case-wise label-oracle routing. More BP iterations, wider search, forced list decoding, and a local X/Z/Y marginalization were also checked privately.

Residuals concentrate in spatial-pair-coupled, list-search inference. The noisy temporal case retains confidently wrong *truncated-list* scores. Fault-component and detector-hotspot associations are descriptive, not causal proofs or Bayes bounds. Private raw summaries, paired reports and residual diagnostics are in `evaluator/hidden/evidence/` and `evaluator/hidden/scientific_selection.json`.

**No qualified passing solution exists.** This is explicitly a hard open improvement target, not an achievability claim. Expensive knobs show some approximation headroom but do not certify a 20% improvement within budget. No new candidate was scored on the new hidden data during selection.

## Sampling, isolation, and validation

Every label is L e mod 2 for an unconditional independent Bernoulli mechanism vector e; syndromes are H e mod 2. All 18 seed streams were committed before any decoding. There is no hard-shot filtering, rejection, class balancing or seed search. Actual nonuniform probabilities and the full DEM are public; sampled hidden labels and seeds are not.

The trusted parent snapshots only the candidate's directory. Isolated attempt/champion/adversary candidate subdirectories are allowed; privileged ancestry, collection roots, symlinks and nonregular artifacts are rejected. Candidate input contains only syndromes plus known model assets. Hidden data never enter the worker mount. The full worker JSON/NPZ interface is documented publicly for main's audit.

Evaluation uses bwrap with private user/PID/network namespaces, `--as-pid-1`, a private proc/dev/tmp, and explicit read-only participant/submission/request mounts. Seccomp blocks process/thread creation and cross-process memory access. Host environment is cleared. CPU is measured by trusted parent wait4, not worker-reported metadata. A trusted two-second CPU burn increased measured CPU by {probe['measured_cpu_burn_increment']:.6f} seconds before freeze. No isolation fallback is permitted.

All 11 scientific/unit tests and all final validation checks pass. They cover Stim parity semantics, four independent logical homologies, unconditional sampling moments, exact seed reproduction, baseline identity and batch invariance, strict prediction schema, submission-path rules, self-contained runtime, freeze integrity, CPU accounting, and valid-failure versus invalid-output handling. Raw reports are under `attempts/`.

All {len(original['artifacts'])} original frozen artifacts and the original champion code hashes still match. Bundled runtime is about 313 MiB of real files, not external symlinks; `/usr/bin/python3` loads it in isolation. The original frozen task and no other concept were edited.

## Main handoff

Run from a context allowed to create the bwrap namespaces (an escalated exec outside the parent sandbox is required on this host):

```
/usr/bin/python3 evaluator/evaluate.py --submission attempts/v_1/submission.py --split both --report attempts/v_1_result.json
```

The paths above are relative to generation_2. Preserve the candidate snapshot before hidden evaluation and avoid adaptive holdout reuse. `valid=true, passed=false` is an ordinary target failure; invalid submissions have separate status and reason. The private evaluator, hidden data, seeds and stress portfolios must never be mounted for the fresh coding agent. Only `participant/` and its output directory belong in that agent's filesystem view.
"""
    add_text(GENERATION / "BUILD_AUDIT.md", audit)
    add_text(GENERATION / "CHANGED_FILES.md", """# Changed paths

All task assets are new under `concept_1/generations/generation_2/`:

- `participant/TASK.md`, `participant/input/{API.md,SCIENCE.md,models.py,worker.py,run_public.py,target.json}`
- `participant/input/{cases/,calibration/,runtime/,runtime_versions.json,requirements.lock}`
- `participant/baseline/{submission.py,decoder.cpp,decoder.so,Makefile,README.md}` and `participant/workspace/submission.py`
- `evaluator/{evaluate.py,qualify.py,probe_runtime.py,test_evaluator.py,validate.py}`
- `evaluator/hidden/{build_data.py,freeze.py,seeds.json,challenge/,holdout/,frozen.json,frozen.sha256,evidence/,scientific_selection.json,baseline_provenance.json,baseline_qualification.json,runtime_probe.json,sampling_report.json}`
- `attempts/` raw build, baseline, test and validation reports; `adversary/` isolated validation probes; `champions/` reserved for main.
- `status.json`, `BUILD_AUDIT.md`, and this change inventory.

Supporting stress, knob, compiler, temperature and fallback controls were added only under `concept_1/adversary/stress_harness/`. No original participant/evaluator/frozen/champion artifact or other concept was modified. The runtime and native binaries are copied assets; source edits use apply_patch.
""")
    status = dict(status="READY", mode="A_BASELINE_IMPROVEMENT", generation=2, ratchet_index=1, max_ratchets=3,
        ready_utc=datetime.now(timezone.utc).isoformat(), parent_champion="concept_1/champions/generation_1",
        fresh_runner_launched=False, original_frozen_unchanged=True, targets=frozen["targets"], limits=frozen["limits"],
        freeze_sha256=digest, baseline=dict(failures=427, shots=3072, challenge_failures=212, holdout_failures=215,
            cpu_seconds=baseline["execution"]["cpu_seconds"], core_score=0, worst_family_score=0, resource_score=baseline["resource_score"], valid=True, passed=False),
        tests=dict(scientific_unit_tests=11, scientific_passed=True, validation_passed=True),
        qualified_passing_solution=None, reference_status="HARD_OPEN_NO_QUALIFIED_PASS", main_action="Audit frozen tree and launch fresh one-hour generation-two run")
    (GENERATION / "status.json").write_text(json.dumps(status, indent=2) + "\n")
    print(json.dumps(status, indent=2), flush=True)


if __name__ == "__main__":
    main()
