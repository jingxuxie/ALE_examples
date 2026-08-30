import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
FILES = (
    "evaluator/evaluate.py", "evaluator/runner.py", "evaluator/hidden/teacher.py",
    "evaluator/hidden/generate.py", "evaluator/hidden/target_contract.json",
    "evaluator/hidden/test_inputs.json", "evaluator/hidden/test_labels.json",
    "evaluator/hidden/certificates.json", "evaluator/hidden/teacher_summary.json",
    "participant/input/train.json", "participant/input/validation_inputs.json",
    "participant/input/validation_labels.json", "participant/input/PHYSICS.md",
    "participant/input/DISTRIBUTION.md", "participant/TASK.md"
)


def main():
    manifest = {"algorithm": "sha256", "sha256": {
        filename: hashlib.sha256((ROOT / filename).read_bytes()).hexdigest() for filename in FILES}}
    ledger = json.loads((ROOT / "evaluator/hidden/generation_seeds.json").read_text())
    if ledger["contract_sha256"] != manifest["sha256"]["evaluator/hidden/target_contract.json"]:
        raise RuntimeError("Target contract was changed after generation began")
    (ROOT / "evaluator/hidden/integrity.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print("Sealed %d trusted files" % len(FILES))


if __name__ == "__main__":
    main()
