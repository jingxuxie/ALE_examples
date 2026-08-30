"""Invoke the immutable trusted scorer, relocating scratch only."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import resource
import sys
import tempfile


ROOT = Path(__file__).resolve().parent
CONCEPT = ROOT.parents[1]
sys.dont_write_bytecode = True
sys.path = [str(CONCEPT / "evaluator")] + [path for path in sys.path if path and Path(path).resolve() != ROOT]
import evaluate as frozen


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--split", choices=("validation", "hidden"), default="validation")
    arguments = parser.parse_args()
    report_path = ROOT / f"frozen_{arguments.split}_report.json"
    if report_path.exists():
        raise RuntimeError("This sidecar split has already been evaluated; refusing repeat selection")
    training = json.loads((ROOT / "training_report.json").read_text())
    previous_cpu = training["cpu_seconds"]
    validation_report = ROOT / "frozen_validation_report.json"
    if validation_report.exists():
        previous_cpu += json.loads(validation_report.read_text())["sidecar_evaluation_cpu_seconds"]
    if arguments.split == "hidden" and training["selected"]["validation"]["objective"] > 1.20:
        raise RuntimeError("Public validation is not promising enough for the reserved hidden evaluation")
    if previous_cpu > 1000:
        raise RuntimeError("Insufficient CPU reserve for a full 180-second frozen invocation")
    if not (CONCEPT / "attempts" / ".scratch").is_dir():
        raise RuntimeError("Frozen scratch parent is absent; refusing any directory creation outside the sidecar")
    selection = json.loads((ROOT / "selection.json").read_text())
    assets = [ROOT / "solve.py", ROOT / "selection.json", ROOT / "projection_2.npz", ROOT / "projection_3.npz"]
    assets += [ROOT / name for names in selection["models"].values() for name in names]
    asset_hashes = {path.name: hashlib.sha256(path.read_bytes()).hexdigest() for path in assets}
    if arguments.split == "hidden":
        (ROOT / "pre_hidden_asset_manifest.json").write_text(json.dumps(asset_hashes, indent=2) + "\n")
    scratch = ROOT / "scratch"
    scratch.mkdir(exist_ok=True)
    original_temporary_directory = tempfile.TemporaryDirectory

    def sidecar_temporary_directory(*arguments, **keywords):
        keywords["dir"] = scratch
        return original_temporary_directory(*arguments, **keywords)

    frozen.tempfile.TemporaryDirectory = sidecar_temporary_directory
    before_self = resource.getrusage(resource.RUSAGE_SELF)
    before_children = resource.getrusage(resource.RUSAGE_CHILDREN)
    result = frozen.evaluate(ROOT, split=arguments.split)
    after_self = resource.getrusage(resource.RUSAGE_SELF)
    after_children = resource.getrusage(resource.RUSAGE_CHILDREN)
    elapsed_cpu = (after_self.ru_utime + after_self.ru_stime + after_children.ru_utime + after_children.ru_stime
                   - before_self.ru_utime - before_self.ru_stime - before_children.ru_utime - before_children.ru_stime)
    result["sidecar_evaluation_cpu_seconds"] = elapsed_cpu
    result["candidate_asset_sha256"] = asset_hashes
    result["sidecar_accumulated_cpu_seconds"] = previous_cpu + elapsed_cpu
    result["integration"] = "Unmodified frozen evaluate()/sandbox/score/limits; only temporary-directory placement redirected inside this sidecar. Candidate remains a sandboxed subprocess."
    report_path.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    print(json.dumps(result, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
