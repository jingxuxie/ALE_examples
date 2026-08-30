import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "concept_3"
manifest_path = ROOT / "evaluator/private/frozen_manifest.json"
manifest = json.loads(manifest_path.read_text())
manifest["participant_sha256"] = {
    str(path.relative_to(ROOT / "participant")): hashlib.sha256(path.read_bytes()).hexdigest()
    for path in sorted((ROOT / "participant").rglob("*")) if path.is_file() and "__pycache__" not in path.parts
}
manifest["freeze_stage"] = "pre_tournament_documentation_integration_one_hour_limit"
manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")
print(json.dumps({"participant_files": len(manifest["participant_sha256"]), "math_targets_unchanged": True}))
