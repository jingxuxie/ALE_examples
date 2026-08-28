"""Measure finite-difference shortcuts, deterministic exports and isolated branches."""

import argparse
import importlib.util
import json
from pathlib import Path
import resource
import subprocess
import sys
import time

import build

import numpy as np

from evaluator import arrays, errors, score_details


def module_at(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def finite_difference(data, value_function, step):
    answer = []
    for wavevector in data["q_cart"]:
        components = []
        for axis in np.eye(3):
            components.append((value_function(data, wavevector + step * axis) - value_function(data, wavevector - step * axis)) / (2 * step))
        answer.append(components)
    return np.asarray(answer)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--worker", choices=("baseline", "strong"))
    parser.add_argument("--branch", choices=("derivative", "mode_response"))
    parser.add_argument("--input", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.worker:
        if not args.output.resolve().is_relative_to(build.POLAR):
            parser.error("worker output must remain inside polar")
        solver = build.POLAR / "participant/workspace/solve.py" if args.worker == "baseline" else build.REFERENCE / "solve.py"
        module = module_at(solver, "measured_solver")
        data = arrays(args.input)
        started = time.perf_counter()
        output = getattr(module, args.branch)(data)
        elapsed = time.perf_counter() - started
        checksum = float(sum(np.linalg.norm(value) for value in output)) if isinstance(output, tuple) else float(np.linalg.norm(output))
        build.write_json(args.output, {"solver": args.worker, "branch": args.branch, "seconds": elapsed,
                                      "isolated_process_max_rss_kb": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
                                      "output_norm_sum": checksum})
        return
    folder = build.POLAR / "private/reference/author_measurements/audit"
    folder.mkdir(parents=True, exist_ok=True)
    baseline_module = module_at(build.POLAR / "participant/workspace/solve.py", "baseline")
    manifest = json.loads((build.PRIVATE / "challenge_pool/manifest.json").read_text())
    calibration = json.loads((build.POLAR / "private/reference/author_measurements/initial/calibration.json").read_text())
    records, deterministic = [], []
    for case in manifest:
        input_path = build.PRIVATE / case["input"]
        data, reference, baseline = arrays(input_path), arrays(build.PRIVATE / case["reference"]), arrays(build.PRIVATE / case["baseline"])
        measurements = []
        for solver in ("baseline", "strong"):
            for branch in ("derivative", "mode_response"):
                output = folder / "branches" / f"{case['id']}_{solver}_{branch}.json"
                subprocess.run([sys.executable, str(Path(__file__).resolve()), "--worker", solver, "--branch", branch,
                                "--input", str(input_path), "--output", str(output)], check=True, timeout=180)
                measurements.append(json.loads(output.read_text()))
        probes = []
        for step in (1e-6, 1e-7, 1e-8):
            started = time.perf_counter()
            actual_derivative = finite_difference(data, baseline_module.matrix_value, step)
            seconds = time.perf_counter() - started
            actual = dict(reference, derivative=actual_derivative)
            scored = score_details(actual, reference, baseline, case, data)
            output_path = folder / "finite_difference" / f"{case['id']}_{step:.0e}.npz"
            output_path.parent.mkdir(parents=True, exist_ok=True)
            np.savez_compressed(output_path, derivative=actual_derivative)
            probes.append({"step": step, "derivative_score": scored["component_scores"]["polar_derivative"],
                           "derivative_relative_error": scored["errors"]["derivative"], "seconds": seconds,
                           "output": str(output_path.relative_to(build.POLAR))})
        wrong_frame = dict(data, cell=np.eye(3))
        strong = module_at(build.REFERENCE / "solve.py", "strong")
        wrong_response = strong.mode_response(wrong_frame)
        wrong = dict(reference, response=wrong_response[0], velocity=wrong_response[1], branch_velocity=wrong_response[2])
        ablation = score_details(wrong, reference, baseline, case, data)
        records.append({"id": case["id"], "family": case["family"], "split": case["split"], "branches": measurements,
                        "fd_probes": probes, "ignored_cartesian_conversion": ablation})
        print(json.dumps({"id": case["id"], "fd_scores": [probe["derivative_score"] for probe in probes]}), flush=True)
    for family_index, family in enumerate(("NaCl", "SnO2", "TiO2")):
        case = next(item for item in manifest if item["family"] == family and item["split"] == "heldout" and item["near_gamma"])
        phonon, base, _ = build.material(family)
        regenerated, regenerated_reference, _ = build.make_case(phonon, base, np.random.default_rng(np.random.SeedSequence(case["seed"])),
                                                               case["derivative_queries"], True, True)
        old_input, old_reference = arrays(build.PRIVATE / case["input"]), arrays(build.PRIVATE / case["reference"])
        equal = all(np.array_equal(old_input[key], regenerated[key]) for key in old_input)
        equal_reference = all(np.array_equal(old_reference[key], regenerated_reference[key]) for key in old_reference)
        if not equal or not equal_reference:
            raise RuntimeError(f"deterministic rebuild failed: {family}")
        fresh_rng = np.random.default_rng(np.random.SeedSequence([884209, family_index, 1, 1, 1927]))
        fresh, _, _ = build.make_case(phonon, base, fresh_rng, case["derivative_queries"], True, True)
        if np.array_equal(fresh["q_cart"], old_input["q_cart"]):
            raise RuntimeError("fresh heldout did not change queries")
        deterministic.append({"family": family, "input_arrays_identical": equal, "reference_arrays_identical": equal_reference,
                              "fresh_queries_different": True})
    summary = {"cases": records, "deterministic_checks": deterministic,
               "reference_score": calibration["strong_score"], "baseline_score": calibration["baseline_score"],
               "fd_scope": "Derivative branch only. Response inputs/outputs are not solved by the FD audit. Reference response used only to isolate derivative scoring.",
               "fd_step_means": {str(step): float(np.mean([record["fd_probes"][index]["derivative_score"] for record in records]))
                                 for index, step in enumerate((1e-6, 1e-7, 1e-8))},
               "branch_memory_policy": "Fresh worker process per solver/branch; peak RSS includes imports, input, and that branch, not the other branch."}
    build.write_json(folder / "report.json", summary)
    print(json.dumps({"fd_step_means": summary["fd_step_means"], "deterministic_checks": deterministic}, indent=2))


if __name__ == "__main__":
    main()
