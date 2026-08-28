import argparse
import copy
import datetime
import hashlib
import json
import math
import os
from pathlib import Path
import resource
import shutil
import sys
import time


SIDE = Path(__file__).resolve().parent
ROOT = SIDE.parents[1]
PILOT = ROOT / "pilots" / "c02_multiscale_protection"
for variable in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS", "NUMBA_NUM_THREADS"):
    os.environ[variable] = "1"
os.environ["NUMBA_CACHE_DIR"] = str(SIDE / "cache" / "numba")
os.environ["MPLCONFIGDIR"] = str(SIDE / "cache" / "matplotlib")
os.environ["XDG_CACHE_HOME"] = str(SIDE / "cache")
sys.dont_write_bytecode = True
sys.path.insert(0, str(PILOT / "private" / "reference"))
sys.path.insert(0, str(PILOT / "private"))
sys.path.insert(0, str(ROOT / "authoring"))
LEVELS = {"coarse": {"step": 0.1, "bond": 96, "cutoff": 1e-9},
          "fine": {"step": 0.05, "bond": 192, "cutoff": 1e-12},
          "refined": {"step": 0.025, "bond": 384, "cutoff": 1e-13}}


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def save(path, value):
    path = SIDE / path
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        raise RuntimeError("refusing to overwrite " + str(path))
    temporary = path.with_suffix(path.suffix + ".pending")
    temporary.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")
    temporary.replace(path)


def bounds(case, parameters):
    settings = case["experiment"]
    length, spin = settings["length"], settings["spin"]
    checks = {"length": 24 <= length <= 64, "spin": spin in (0.5, 1),
              "protection_strength": 0 <= settings["V"] <= 12,
              "times": case["times"][0] == 0 and case["times"][-1] <= 10
              and all(after > before for before, after in zip(case["times"], case["times"][1:])),
              "profiles": len(settings["profile"]) == len(settings["coefficients"]) == length,
              "pairs": all(0 <= left < right < length for left, right in case["pairs"]),
              "parameters": 0.025 <= parameters[0] <= 0.30 and 0.025 <= parameters[1] <= 0.30 and -0.25 <= parameters[2] <= 0.25,
              "initial_target": all(((-spin if site == 0 else (-1) ** (site - 1) * spin)
                                     + (-1) ** site * spin) == 0 for site in range(length))}
    if not all(checks.values()):
        raise ValueError("public-contract or physical initial-state violation: " + str(checks))
    return checks


def freeze():
    from build import make_case
    from engine import infer_parameters
    if (SIDE / "manifest.json").exists():
        raise RuntimeError("already frozen")
    metadata_path = ROOT / "authoring/runs/c02_multiscale_protection/screening/result.json"
    metadata = json.loads(metadata_path.read_text())
    if metadata["exit_code"] != 0 or not metadata["participant_unchanged"]:
        raise RuntimeError("completed unchanged submission required")
    original = Path(metadata["attempt"])
    snapshot = SIDE / "submission_snapshot"
    snapshot.mkdir()
    for name, expected in metadata["submission_sha256"].items():
        if sha(original / name) != expected:
            raise RuntimeError("completed submission changed: " + name)
        destination = snapshot / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(original / name, destination)
        if sha(destination) != expected:
            raise RuntimeError("snapshot hash mismatch")
    base, parameters = make_case(18334, "inhomogeneous_weak", 0)
    fitted, fit_audit = infer_parameters(base)
    entries = []
    for identifier, strength, terminal in (("weak_spin1_V0p5_L32_T8", 0.5, 8), ("weak_spin1_V1_L32_T10", 1.0, 10)):
        case = copy.deepcopy(base)
        case["experiment"].update(length=32, spin=1.0, V=strength)
        case["times"] = [0.0, 0.2, 0.7, 1.5, 3.0, 4.5, 6.0, 8.0] + ([10.0] if terminal == 10 else [])
        checks = bounds(case, parameters)
        relative = "cases/" + identifier + ".json"
        save(relative, case)
        entries.append({"id": identifier, "case_path": relative, "case_file_sha256": sha(SIDE / relative),
                        "solver_case_sha256": hashlib.sha256(json.dumps(case, sort_keys=True).encode()).hexdigest(),
                        "true_parameters": parameters, "public_contract": checks})
    sources = [PILOT / "private/reference/build.py", PILOT / "private/reference/charge_engine.py",
               PILOT / "private/reference/engine.py", PILOT / "private/reference/charge_engine_small_validation.json",
               PILOT / "participant/workspace/dense_cluster.py", PILOT / "participant/input/protocol.md",
               PILOT / "private/evaluator.py"]
    manifest = {"frozen_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(), "seed": 18334,
                "source_family": "inhomogeneous_weak", "cases": entries, "levels": LEVELS,
                "acceptance_threshold": 0.97, "original_submission": str(original),
                "submission_sha256": metadata["submission_sha256"], "launch_metadata_sha256": sha(metadata_path),
                "original_authoring_seconds": metadata["elapsed_seconds"],
                "source_sha256": {str(path.relative_to(ROOT)): sha(path) for path in sources},
                "calibration_fit": {"parameters": fitted, "audit": fit_audit,
                                    "maximum_parameter_error": max(abs(actual - truth) for actual, truth in zip(fitted, parameters))}}
    save("manifest.json", manifest)
    print(json.dumps(manifest), flush=True)


def load(identifier):
    manifest = json.loads((SIDE / "manifest.json").read_text())
    entry = next(entry for entry in manifest["cases"] if entry["id"] == identifier)
    path = SIDE / entry["case_path"]
    if sha(path) != entry["case_file_sha256"]:
        raise RuntimeError("frozen input changed")
    case = json.loads(path.read_text())
    bounds(case, entry["true_parameters"])
    return manifest, entry, case


def reference(identifier, level, cpu):
    manifest, entry, case = load(identifier)
    if cpu is not None:
        os.sched_setaffinity(0, {cpu})
    if level == "refined":
        previous = json.loads((SIDE / "references" / identifier / "convergence_coarse_fine.json").read_text())
        if previous["accepted"]:
            raise RuntimeError("refinement is unnecessary")
    from charge_engine import predict
    print(json.dumps({"start_reference": identifier, "level": level, "settings": LEVELS[level], "cpu": sorted(os.sched_getaffinity(0))}), flush=True)
    prediction, audit = predict(case["experiment"], entry["true_parameters"], case["times"], case["pairs"], **LEVELS[level])
    audit["max_rss_kib"] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    audit["cpu_seconds"] = resource.getrusage(resource.RUSAGE_SELF).ru_utime + resource.getrusage(resource.RUSAGE_SELF).ru_stime
    save("references/" + identifier + "/" + level + ".json", {"id": identifier, "case_file_sha256": entry["case_file_sha256"], "prediction": prediction, "audit": audit})
    print(json.dumps({"finished_reference": identifier, "level": level, "audit": audit}), flush=True)


def assess(identifier, finer):
    import numpy as np
    from evaluator import score_result
    manifest, entry, case = load(identifier)
    coarser = "coarse" if finer == "fine" else "fine"
    paths = [SIDE / "references" / identifier / (level + ".json") for level in (coarser, finer)]
    coarse, fine = [json.loads(path.read_text()) for path in paths]
    scores, errors = score_result(coarse["prediction"], fine["prediction"])
    differences, block_bounds = {}, {"parameters": 1.0}
    physical = True
    for name in ("density", "violation", "correlation"):
        values = np.asarray(fine["prediction"][name])
        differences[name] = float(np.max(np.abs(values - np.asarray(coarse["prediction"][name]))))
        block_bounds[name] = math.exp(-math.log(10) * differences[name] / errors[name]["weak_scale"])
        physical &= bool(np.all(np.isfinite(values)))
        if name == "density":
            physical &= bool(np.min(values) >= -1e-7 and np.max(values) <= 1 + 1e-7)
        elif name == "violation":
            physical &= bool(np.min(values) >= -1e-7 and np.max(values) <= 9 + 1e-7)
        else:
            physical &= bool(np.max(np.abs(values)) <= 0.25 + 1e-7)
    diagnostic = float(np.prod(list(block_bounds.values())) ** 0.25)
    physical &= fine["audit"]["conserved_charge_commutator"] <= 1e-11 and fine["audit"]["final_total_charge"] == [0]
    signs = (-1.0) ** np.arange(case["experiment"]["length"])
    charge = np.asarray(fine["prediction"]["density"]) @ signs
    physical &= bool(np.max(np.abs(charge)) <= 1e-8)
    result = {"id": identifier, "coarser": coarser, "finer": finer,
              "reference_sha256": {path.name: sha(path) for path in paths},
              "normalized_convergence_score": diagnostic, "rms_components": scores, "rms_errors": errors,
              "rms_geometric_core": float(np.prod(list(scores.values())) ** 0.25),
              "maximum_differences": differences, "maximum_difference_component_bounds": block_bounds,
              "reference_charge_expectation": charge.tolist(),
              "physical_checks": bool(physical), "accepted": bool(physical and diagnostic >= 0.97),
              "interpretation": "Convergence diagnostic, not a rigorous exact-solution bound."}
    save("references/" + identifier + "/convergence_" + coarser + "_" + finer + ".json", result)
    if result["accepted"]:
        save("references/" + identifier + "/accepted.json", {"reference_path": str(paths[1].relative_to(SIDE)), "reference_sha256": sha(paths[1]), "convergence": result})
    print(json.dumps(result), flush=True)


def evaluate(identifier):
    import numpy as np
    from evaluator import score_result
    from isolated_eval import run_solver
    manifest, entry, case = load(identifier)
    accepted = json.loads((SIDE / "references" / identifier / "accepted.json").read_text())
    if not accepted["convergence"]["accepted"] or accepted["convergence"]["normalized_convergence_score"] < 0.97:
        raise RuntimeError("no accepted converged label")
    reference_path = SIDE / accepted["reference_path"]
    if sha(reference_path) != accepted["reference_sha256"]:
        raise RuntimeError("reference hash changed")
    snapshot = SIDE / "submission_snapshot"
    for name, expected in manifest["submission_sha256"].items():
        if sha(snapshot / name) != expected or sha(Path(manifest["original_submission"]) / name) != expected:
            raise RuntimeError("submission no longer unchanged")
    print(json.dumps({"start_evaluation": identifier, "timeout": 3600, "startup_grace": 30}), flush=True)
    execution = run_solver(snapshot, PILOT / "participant", case, timeout=3600, memory_gib=6, startup_grace=30)
    save("evaluations/" + identifier + "/raw_execution.json", {"case_file_sha256": entry["case_file_sha256"], "reference_sha256": accepted["reference_sha256"], "execution": execution})
    reference = json.loads(reference_path.read_text())["prediction"]
    scores, errors = score_result(execution.get("result", {}) if execution.get("ok") else {}, reference)
    diagnostics = {}
    if execution.get("ok") and all(isinstance(error, dict) for error in errors.values()):
        prediction = execution["result"]
        signs = (-1.0) ** np.arange(case["experiment"]["length"])
        diagnostics["charge_expectation"] = (np.asarray(prediction["density"]) @ signs).tolist()
        diagnostics["reference_charge_expectation"] = (np.asarray(reference["density"]) @ signs).tolist()
        diagnostics["maximum_absolute_charge_expectation"] = max(map(abs, diagnostics["charge_expectation"]))
        diagnostics["parameter_maximum_error"] = float(np.max(np.abs(np.asarray(prediction["parameters"]) - entry["true_parameters"])))
        diagnostics["per_time"] = {}
        for name in ("density", "violation", "correlation"):
            delta = np.asarray(prediction[name]) - np.asarray(reference[name])
            diagnostics["per_time"][name] = {"rmse": np.sqrt(np.mean(delta ** 2, axis=1)).tolist(),
                                             "maximum_error": np.max(np.abs(delta), axis=1).tolist()}
    result = {"id": identifier, "family": "weak_inhomogeneous_spin_one", "components": scores, "errors": errors,
              "geometric_core": float(np.prod(list(scores.values())) ** 0.25),
              "execution": {key: value for key, value in execution.items() if key != "result"},
              "diagnostics": diagnostics,
              "convergence": accepted["convergence"], "public_contract": entry["public_contract"],
              "unchanged_submission": all(sha(snapshot / name) == expected for name, expected in manifest["submission_sha256"].items())}
    save("evaluations/" + identifier + "/score.json", result)
    print(json.dumps(result), flush=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=("freeze", "reference", "assess", "evaluate"))
    parser.add_argument("--case")
    parser.add_argument("--level", choices=LEVELS, default="fine")
    parser.add_argument("--cpu", type=int)
    arguments = parser.parse_args()
    if arguments.action == "freeze":
        freeze()
    elif not arguments.case:
        parser.error("--case is required")
    elif arguments.action == "reference":
        reference(arguments.case, arguments.level, arguments.cpu)
    elif arguments.action == "assess":
        assess(arguments.case, arguments.level)
    else:
        evaluate(arguments.case)


if __name__ == "__main__":
    main()
