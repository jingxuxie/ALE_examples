"""Persist child dependency availability and baseline permutation covariance."""

import ctypes
import json
from pathlib import Path
import platform
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "evaluator"))

import numpy as np

from evaluate import run_guarded
from scoring import parse_predictions


def main():
    settings = json.loads((ROOT / "evaluator/settings.json").read_text())
    submission = ROOT / "participant/baseline"
    code = """
import importlib, json, os, pathlib, resource, sys
result = {"executable": sys.executable, "version": sys.version,
          "affinity": sorted(os.sched_getaffinity(0)),
          "address_space_limit": resource.getrlimit(resource.RLIMIT_AS),
          "cpu_limit": resource.getrlimit(resource.RLIMIT_CPU), "modules": {}}
for name in ("numpy", "scipy", "sklearn"):
    try:
        module = importlib.import_module(name)
        result["modules"][name] = {"version": module.__version__, "path": module.__file__}
    except Exception as error:
        result["modules"][name] = {"error": type(error).__name__ + ": " + str(error)}
pathlib.Path(sys.argv[1]).write_text(json.dumps(result, indent=2))
"""
    with tempfile.TemporaryDirectory(prefix="interface-", dir=ROOT / "evaluator/runs") as temporary:
        scratch = Path(temporary)
        runtime = run_guarded(["/usr/bin/python3", "-c", code, str(scratch / "dependencies.json")],
                              {}, submission, scratch, settings)
        if runtime["failure"]:
            raise RuntimeError(runtime)
        dependency_report = json.loads((scratch / "dependencies.json").read_text())
    dependency_report["required_inference_modules"] = ["numpy"]
    dependency_report["runtime"] = runtime
    dependency_report["kernel"] = platform.release()
    dependency_report["landlock_abi"] = int(ctypes.CDLL(None).syscall(444, 0, 0, 1))
    assert "version" in dependency_report["modules"]["numpy"]
    assert "version" in dependency_report["modules"]["scipy"]
    (ROOT / "adversary/dependency_report.json").write_text(json.dumps(dependency_report, indent=2) + "\n")
    with np.load(ROOT / "participant/input/validation.npz", allow_pickle=False) as archive:
        validation = dict(archive)
    selected = []
    for family in range(4):
        for size in (8, 10):
            selected.extend(np.flatnonzero((validation["family"] == family)
                                           & (validation["n_sites"] == size))[:2])
    inputs = {key: np.concatenate([value[selected], value[selected]])
              for key, value in validation.items() if key != "gaps"}
    rng = np.random.default_rng(19081)
    for index in range(len(selected), 2 * len(selected)):
        size = inputs["n_sites"][index]
        permutation = rng.permutation(size)
        inputs["hopping"][index, :size, :size] = inputs["hopping"][index, :size, :size][np.ix_(permutation, permutation)]
        for key in ("interaction", "potential"):
            inputs[key][index, :size] = inputs[key][index, permutation]
    with tempfile.TemporaryDirectory(prefix="covariance-", dir=ROOT / "evaluator/runs") as temporary:
        scratch = Path(temporary)
        np.savez_compressed(scratch / "inputs.npz", **inputs)
        (scratch / "request.json").write_text(json.dumps({"schema_version": 1,
            "inputs": str(scratch / "inputs.npz"), "n_instances": len(inputs["family"]),
            "target_order": ["charge_gap", "spin_gap"]}))
        runtime = run_guarded(["/usr/bin/python3", str(submission / "solver.py"),
            str(scratch / "request.json"), str(scratch / "predictions.json")], {}, submission, scratch, settings)
        if runtime["failure"]:
            raise RuntimeError(runtime)
        predictions = parse_predictions((scratch / "predictions.json").read_text(), len(inputs["family"]))
    difference = float(np.max(abs(predictions[:len(selected)] - predictions[len(selected):])))
    report = {"paired_rows": len(selected), "max_prediction_permutation_error": difference,
              "runtime": runtime, "passed": difference < 1e-8}
    (ROOT / "adversary/interface_report.json").write_text(json.dumps(report, indent=2) + "\n")
    public_predictions = parse_predictions((ROOT / "attempts/public_development/predictions.json").read_text(), 256)
    np.savez_compressed(ROOT / "attempts/baseline_validation_residuals.npz", predictions=public_predictions,
                        residuals=public_predictions - validation["gaps"], family=validation["family"],
                        n_sites=validation["n_sites"])
    print(json.dumps({"dependencies": dependency_report, "interface": report}, indent=2))
    if not report["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
