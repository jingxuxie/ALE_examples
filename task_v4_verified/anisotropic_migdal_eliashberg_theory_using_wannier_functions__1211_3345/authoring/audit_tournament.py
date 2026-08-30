import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def manifest(directory):
    result = {}
    for path in sorted(directory.rglob("*")):
        if "__pycache__" in path.parts:
            continue
        if path.is_symlink():
            result[str(path.relative_to(directory))] = "symlink:" + str(path.readlink())
        elif path.is_file():
            result[str(path.relative_to(directory))] = hashlib.sha256(path.read_bytes()).hexdigest()
    return result


def main():
    failures = []
    pending = []
    packages = []
    runs = []
    for concept in ("concept_1", "concept_2", "concept_3"):
        directory = ROOT / concept
        missing = [name for name in (
            "participant/TASK.md", "participant/input", "participant/input/FORMAT.md",
            "participant/workspace", "participant/baseline", "evaluator/evaluate.py",
            "evaluator/hidden", "attempts", "champions", "adversary", "status.json",
        ) if not (directory / name).exists()]
        symlinks = [str(path.relative_to(directory))
                    for path in (directory / "participant").rglob("*") if path.is_symlink()]
        if missing or symlinks:
            failures.append({"concept": concept, "missing": missing, "participant_symlinks": symlinks})
        packages.append({"concept": concept, "complete": not missing,
                         "participant_symlinks": symlinks})
    for directory in sorted((ROOT / "authoring" / "runs").glob("concept_*/v_*")):
        identifier = str(directory.relative_to(ROOT / "authoring" / "runs"))
        adjudication_path = directory / "adjudication.json"
        if adjudication_path.exists():
            adjudication = json.loads(adjudication_path.read_text())
            if not adjudication.get("competitive", True):
                runs.append({"run": identifier, "competitive": False,
                             "adjudication": str(adjudication_path.relative_to(ROOT))})
                continue
        result_path = directory / "result.json"
        if not result_path.exists():
            pending.append(identifier)
            continue
        result = json.loads(result_path.read_text())
        frozen = Path(result["frozen_submission"])
        isolation_path = frozen / "isolation.json"
        denial_record = json.loads(isolation_path.read_text()) if isolation_path.exists() else None
        denial_ok = isinstance(denial_record, list) and len(denial_record) == 2 and all(
            isinstance(value, str) and any(error in value for error in (
                "FileNotFoundError", "PermissionError", "Permission denied", "Operation not permitted"
            )) for value in denial_record
        )
        checks = {
            "model_is_ultima_alpha": result.get("model") == "ultima-alpha",
            "one_hour_limit": result.get("time_limit_seconds") == 3600,
            "started_empty": result.get("output_initially_empty") is True,
            "participant_read_only": result.get("participant_access") == "read-only",
            "participant_unchanged": result.get("participant_unchanged") is True,
            "frozen_manifest_intact": result.get("submission_manifest") == manifest(frozen),
            "both_private_aliases_denied": denial_ok,
            "evaluation_complete": (directory / "evaluation_complete.json").is_file(),
        }
        failed = [name for name, success in checks.items() if not success]
        if failed:
            failures.append({"run": identifier, "failed_checks": failed})
        runs.append({"run": identifier, "competitive": True, "checks": checks,
                     "timed_out": result["timed_out"], "elapsed_seconds": result["elapsed_seconds"]})
    report = {"passed": not failures and not pending, "failures": failures,
              "pending": pending, "packages": packages, "runs": runs,
              "scope": "Packaging and recorded isolation/integrity, not scientific accuracy or achievability."}
    destination = ROOT / "authoring" / "tournament_audit.json"
    destination.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({key: report[key] for key in ("passed", "failures", "pending")}))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
