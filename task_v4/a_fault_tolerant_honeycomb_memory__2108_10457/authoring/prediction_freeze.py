from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONCEPT = ROOT / "concept_3"


def main():
    generic = CONCEPT / "evaluator" / "frozen.json"
    dedicated = CONCEPT / "evaluator" / "prediction_frozen.json"
    if dedicated.exists():
        raise RuntimeError("compatibility revision already frozen")
    original = json.loads(generic.read_text())
    interface_changes = {"participant/task.md", "evaluator/evaluate.py", "evaluator/scoring.py"}
    for relative, expected in original["sha256"].items():
        if relative not in interface_changes and hashlib.sha256((CONCEPT / relative).read_bytes()).hexdigest() != expected:
            raise ValueError("non-interface artifact changed: " + relative)
    frozen = {"threshold_frozen_utc": original["frozen_utc"],
              "interface_revision_utc": datetime.now(timezone.utc).isoformat(),
              "interface_revision": "TASK uppercase and 200-300 words; details moved to INTERFACE; standardized output fields only. Target, thresholds, original counts, split and score mathematics unchanged after first baseline.",
              "sandbox_sha256": original["sandbox_sha256"], "sha256": {}}
    paths = list((CONCEPT / "participant").rglob("*")) + list((CONCEPT / "evaluator" / "hidden").rglob("*"))
    paths += [CONCEPT / "evaluator" / name for name in ["protocol.json", "evaluate.py", "scoring.py"]]
    for path in sorted(paths):
        if path.is_file() and "__pycache__" not in path.parts and path.suffix != ".pyc":
            frozen["sha256"][str(path.relative_to(CONCEPT))] = hashlib.sha256(path.read_bytes()).hexdigest()
    text = json.dumps(frozen, indent=2) + "\n"
    dedicated.write_text(text)
    generic.write_text(text)
    print("Interface compatibility revision frozen; original data and thresholds verified unchanged.")


if __name__ == "__main__":
    main()
