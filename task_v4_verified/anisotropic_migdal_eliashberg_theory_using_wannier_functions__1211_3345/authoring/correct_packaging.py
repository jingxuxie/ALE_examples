import datetime
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONCEPT = ROOT / "concept_1"
seal_path = CONCEPT / "evaluator" / "hidden" / "prelaunch_seal.json"
status_path = CONCEPT / "status.json"
old_bytes = seal_path.read_bytes()
seal = json.loads(old_bytes)
for relative, expected in seal["files"].items():
    actual = hashlib.sha256((CONCEPT / relative).read_bytes()).hexdigest()
    if actual != expected and relative not in {"participant/TASK.md", "participant/input/FORMAT.md"}:
        raise RuntimeError("Unexpected change to sealed scientific asset: " + relative)
archive = ROOT / "authoring" / "runs" / "concept_1" / "v_1"
if not (archive / "pre_correction_seal.json").exists():
    (archive / "pre_correction_seal.json").write_bytes(old_bytes)
seal["files"]["participant/TASK.md"] = hashlib.sha256((CONCEPT / "participant" / "TASK.md").read_bytes()).hexdigest()
seal["files"]["participant/input/FORMAT.md"] = hashlib.sha256((CONCEPT / "participant" / "input" / "FORMAT.md").read_bytes()).hexdigest()
seal["packaging_correction"] = {
    "time_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    "reason": "Place the mission inside the participant allowlist and make its paths participant-relative.",
    "prior_seal_sha256": hashlib.sha256(old_bytes).hexdigest(),
    "scientific_assets_and_targets_unchanged": True,
    "invalid_launch_excluded": "concept_1/v_1",
}
seal_path.write_text(json.dumps(seal, indent=2) + "\n")
status = json.loads(status_path.read_text())
status["paths"]["task"] = "participant/TASK.md"
status["prelaunch_sealed_files"] = len(seal["files"])
status["packaging_correction"] = seal["packaging_correction"]
status_path.write_text(json.dumps(status, indent=2) + "\n")
print(json.dumps({"scientific_assets_unchanged": True, "sealed_files": len(seal["files"]),
                  "participant_task_present": True, "competitive_attempt": "v_2"}))
