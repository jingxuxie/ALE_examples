import argparse
import datetime
import hashlib
import json
from pathlib import Path
import shutil


ROOT = Path(__file__).resolve().parents[1]
ACTIVE = ROOT / "concept_1"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify_seal(base, seal):
    for relative, expected in seal["files"].items():
        if digest(base / relative) != expected:
            raise RuntimeError("Seal mismatch: " + relative)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--generation", required=True, type=int, choices=(2, 3))
    parser.add_argument("--previous-attempt", required=True)
    parser.add_argument("--next-attempt", required=True)
    parser.add_argument("--dry-run", action="store_true")
    arguments = parser.parse_args()
    generation_root = ACTIVE / "adversary" / ("generation_" + str(arguments.generation))
    pending = generation_root / "package" / "concept_1"
    backup = generation_root / "activation_previous"
    runs = ROOT / "authoring" / "runs" / "concept_1"
    completion = runs / arguments.previous_attempt / "evaluation_complete.json"
    if not json.loads(completion.read_text())["passed"]:
        raise RuntimeError("Previous champion must pass its own immutable generation")
    for run in runs.glob("v_*"):
        if (run / "adjudication.json").exists():
            adjudication = json.loads((run / "adjudication.json").read_text())
            if not adjudication.get("competitive", True):
                continue
        if not (run / "evaluation_complete.json").exists():
            raise RuntimeError("Previous trial is not completely scored: " + run.name)
    if (runs / arguments.next_attempt).exists() or (ACTIVE / "attempts" / arguments.next_attempt).exists():
        raise RuntimeError("Next fresh attempt must be unused")
    for relative in ("participant/TASK.md", "participant/input/FORMAT.md", "evaluator/evaluate.py"):
        if not (pending / relative).is_file():
            raise RuntimeError("Incomplete pending package: " + relative)
    if any(path.is_symlink() for path in (pending / "participant").rglob("*")):
        raise RuntimeError("Participant symlinks are forbidden")
    seal = json.loads((pending / "evaluator/hidden/prelaunch_seal.json").read_text())
    verify_seal(pending, seal)
    if digest(pending.parent / "authoring/sandbox_runner.py") != digest(ROOT / "authoring/sandbox_runner.py"):
        raise RuntimeError("Shared evaluation harness would change")
    for relative in ("participant/baseline/solve.py", "participant/workspace/solve.py"):
        if digest(pending / relative) != digest(ACTIVE / relative):
            raise RuntimeError("Previously public starting code must remain unchanged: " + relative)
    record = {
        "concept": "concept_1", "ratchet_generation": arguments.generation,
        "pending_package": str(pending), "previous_active_backup": str(backup),
        "sealed_files_verified": len(seal["files"]), "shared_harness_unchanged": True,
        "previous_public_starting_code_unchanged": True,
        "previous_passing_attempt": arguments.previous_attempt,
        "competitive_attempt": arguments.next_attempt,
        "dry_run": arguments.dry_run,
    }
    if arguments.dry_run:
        print(json.dumps(record), flush=True)
        return
    backup.mkdir(exist_ok=False)
    for name in ("participant", "evaluator"):
        (ACTIVE / name).rename(backup / name)
        shutil.copytree(pending / name, ACTIVE / name, symlinks=True)
    for name in ("attempts", "adversary", "champions"):
        for source in (pending / name).rglob("*"):
            if not source.is_file():
                continue
            if source.is_symlink():
                raise RuntimeError("Unexpected private evidence symlink")
            relative = source.relative_to(pending / name)
            if name == "attempts" and relative.parts[0].startswith("v_"):
                raise RuntimeError("Refusing to overwrite a fresh submission")
            destination = ACTIVE / name / relative
            if destination.exists():
                previous = backup / "private_evidence" / name / relative
                previous.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(destination, previous)
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, destination)
    for name in ("TASK.md", "status.json"):
        if (ACTIVE / name).exists():
            shutil.copy2(ACTIVE / name, backup / name)
        shutil.copy2(pending / name, ACTIVE / name)
    verify_seal(ACTIVE, seal)
    record["activated_utc"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
    destination = ROOT / "authoring" / ("activation_concept_1_generation_" + str(arguments.generation) + ".json")
    destination.write_text(json.dumps(record, indent=2) + "\n")
    print(json.dumps(record), flush=True)


if __name__ == "__main__":
    main()
