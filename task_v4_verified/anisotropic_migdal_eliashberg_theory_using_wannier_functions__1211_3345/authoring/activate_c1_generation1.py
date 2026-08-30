import datetime
import hashlib
import json
from pathlib import Path
import shutil


ROOT = Path(__file__).resolve().parents[1]
ACTIVE = ROOT / "concept_1"
PENDING = ACTIVE / "adversary" / "generation_1" / "package" / "concept_1"
BACKUP = ACTIVE / "adversary" / "generation_1" / "activation_previous"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify_seal(base, seal):
    for relative, expected in seal["files"].items():
        if digest(base / relative) != expected:
            raise RuntimeError("Seal mismatch: " + relative)


def main():
    completion = ROOT / "authoring" / "runs" / "concept_1" / "v_2" / "evaluation_complete.json"
    if not json.loads(completion.read_text())["passed"]:
        raise RuntimeError("A passing first-generation champion is required")
    for relative in ("participant/TASK.md", "participant/input/FORMAT.md", "evaluator/evaluate.py"):
        if not (PENDING / relative).is_file():
            raise RuntimeError("Incomplete pending package: " + relative)
    if any(path.is_symlink() for path in (PENDING / "participant").rglob("*")):
        raise RuntimeError("Participant symlinks are forbidden")
    seal = json.loads((PENDING / "evaluator" / "hidden" / "prelaunch_seal.json").read_text())
    verify_seal(PENDING, seal)
    if digest(PENDING / "../authoring/sandbox_runner.py") != digest(ROOT / "authoring/sandbox_runner.py"):
        raise RuntimeError("Shared harness would change")
    if digest(PENDING / "participant/baseline/solve.py") != digest(ACTIVE / "participant/baseline/solve.py"):
        raise RuntimeError("Only the previously public weak baseline may be supplied")
    BACKUP.mkdir(exist_ok=False)
    for name in ("participant", "evaluator"):
        (ACTIVE / name).rename(BACKUP / name)
        shutil.copytree(PENDING / name, ACTIVE / name, symlinks=True)
    for name in ("attempts", "adversary", "champions"):
        for source in (PENDING / name).rglob("*"):
            if not source.is_file():
                continue
            if source.is_symlink():
                raise RuntimeError("Unexpected evidence symlink")
            relative = source.relative_to(PENDING / name)
            if name == "attempts" and relative.parts[0].startswith("v_"):
                raise RuntimeError("Refusing to overwrite a fresh submission")
            destination = ACTIVE / name / relative
            if destination.exists():
                previous = BACKUP / "private_evidence" / name / relative
                previous.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(destination, previous)
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, destination)
    for name in ("TASK.md", "status.json"):
        if (ACTIVE / name).exists():
            shutil.copy2(ACTIVE / name, BACKUP / name)
        shutil.copy2(PENDING / name, ACTIVE / name)
    verify_seal(ACTIVE, seal)
    record = {
        "concept": "concept_1", "ratchet_generation": 1,
        "activated_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "pending_package": str(PENDING), "previous_active_backup": str(BACKUP),
        "sealed_files_verified": len(seal["files"]), "shared_harness_unchanged": True,
        "previous_fresh_code_private": True, "competitive_attempt": "v_3",
        "old_champion_core": 0.8, "old_champion_worst_family": 0.5,
        "target_core": 0.9, "target_worst_family": 0.75,
    }
    (ROOT / "authoring" / "activation_concept_1_generation_1.json").write_text(json.dumps(record, indent=2) + "\n")
    print(json.dumps(record), flush=True)


if __name__ == "__main__":
    main()
