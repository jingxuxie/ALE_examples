import argparse
import datetime
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import sys
import time


ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("concept", type=int)
    parser.add_argument("--generation", type=int, default=1)
    parser.add_argument("--evaluator")
    arguments = parser.parse_args()
    concept = ROOT / f"concept_{arguments.concept}"
    attempts = concept / "attempts"
    name = f"v_{arguments.generation}"
    metadata_path = attempts / (name + ".metadata.json")
    while True:
        try:
            metadata = json.loads(metadata_path.read_text())
        except (FileNotFoundError, json.JSONDecodeError):
            metadata = {}
        if "finished_at" in metadata:
            break
        time.sleep(1)
    output = attempts / name
    frozen = attempts / (name + ".frozen")
    if frozen.exists():
        raise RuntimeError("refusing to overwrite an existing frozen attempt")
    audit = {"frozen_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
             "source": str(output), "frozen": str(frozen), "original_metadata": metadata_path.name}
    try:
        if arguments.concept == 1:
            total = 0
            for path in output.rglob("*"):
                if path.is_symlink() or (not path.is_file() and not path.is_dir()):
                    raise ValueError("submission contains a link or special file")
                if path.is_file():
                    total += path.stat().st_size
            if total > 128 * 1024**2:
                raise ValueError("submission exceeds 128 MiB")
            shutil.copytree(output, frozen)
        else:
            frozen.mkdir()
            relative = Path("witness.json") if arguments.concept == 2 else Path("submission/witness.json")
            source = output / relative
            if arguments.concept == 3 and not source.exists() and (output / "witness.json").exists():
                source = output / "witness.json"
                relative = Path("witness.json")
            if source.is_symlink() or source.parent.is_symlink():
                raise ValueError("witness links are forbidden")
            if source.exists():
                if not source.is_file() or source.stat().st_size > 8 * 1024**2:
                    raise ValueError("witness is not a bounded regular file")
                (frozen / relative).parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, frozen / relative)
        audit["sha256"] = {str(path.relative_to(frozen)): hashlib.sha256(path.read_bytes()).hexdigest()
                           for path in sorted(frozen.rglob("*")) if path.is_file()}
        sys.dont_write_bytecode = True
        evaluator = Path(arguments.evaluator).resolve() if arguments.evaluator else concept / "evaluator/evaluate.py"
        audit["evaluator"] = str(evaluator)
        audit["evaluator_sha256"] = hashlib.sha256(evaluator.read_bytes()).hexdigest()
        specification = importlib.util.spec_from_file_location("task_evaluator", evaluator)
        module = importlib.util.module_from_spec(specification)
        specification.loader.exec_module(module)
        result = module.evaluate(frozen)
    except Exception as error:
        audit["error"] = str(error)
        result = {"core_score": 0, "worst_family_score": 0, "resource_score": 0,
                  "valid": False, "passed": False, "reason": str(error)}
    result["submission_snapshot"] = str(frozen.relative_to(concept))
    result["model"] = metadata.get("model")
    result["attempt_seconds"] = metadata.get("elapsed_seconds")
    result["attempt_timed_out"] = metadata.get("timed_out")
    (attempts / (name + ".freeze.json")).write_text(json.dumps(audit, indent=2) + "\n")
    (attempts / (name + ".score.json")).write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({key: value for key, value in result.items() if key not in ("cases", "families")}, indent=2))


if __name__ == "__main__":
    main()
