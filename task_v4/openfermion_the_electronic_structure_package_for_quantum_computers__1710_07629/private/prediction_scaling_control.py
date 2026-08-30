import hashlib
import importlib.util
import json
import os
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def main():
    available = sorted(os.sched_getaffinity(0))
    selected_cpu = 190 if 190 in available else available[-1]
    os.sched_setaffinity(0, {selected_cpu})
    for variable in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS", "BLIS_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
        os.environ[variable] = "1"
    sys.dont_write_bytecode = True
    import numpy as np

    generation = ROOT / "concept_3/generations/generation_1"
    evaluator_path = generation / "evaluator/evaluate.py"
    sys.path.insert(0, str(evaluator_path.parent))
    specification = importlib.util.spec_from_file_location("trusted_prediction_evaluator", evaluator_path)
    evaluator = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(evaluator)
    settings = json.loads((generation / "evaluator/settings.json").read_text())
    settings.update(wall_seconds=600, cpu_seconds=600)
    submission = generation / "participant/baseline_exact"
    evaluator.check_submission(submission, settings)
    destination = ROOT / "concept_3/adversary/fullbatch_scaling_control"
    destination.mkdir(exist_ok=True)
    with np.load(generation / "evaluator/hidden/test.npz", allow_pickle=False) as archive:
        inputs = {key: archive[key].copy() for key in evaluator.INPUT_KEYS}
        labels = archive["gaps"].copy()
    with tempfile.TemporaryDirectory(prefix="scratch-", dir=destination) as temporary:
        scratch = Path(temporary).resolve()
        input_path = scratch / "inputs.npz"
        request_path = scratch / "request.json"
        output_path = scratch / "predictions.json"
        np.savez_compressed(input_path, **inputs)
        request_path.write_text(json.dumps({"schema_version": 1, "inputs": str(input_path), "n_instances": len(labels), "target_order": ["charge_gap", "spin_gap"]}))
        runtime = evaluator.run_guarded(["/usr/bin/python3", "-B", str(submission / "solver.py"), str(request_path), str(output_path)], {"HUBBARD_ASSET_DIR": str(generation / "participant/input")}, submission, scratch, settings)
        report = {"budget_matched": False, "official_inference_limit_seconds": 25, "control_limit_seconds": 600, "official_passed": False, "purpose": "Separate accuracy from exponential-sector runtime scaling for the unchanged supplied champion", "selected_cpu": selected_cpu, "runtime": runtime, "native_source_sha256": {name: hashlib.sha256((submission / name).read_bytes()).hexdigest() for name in ("solver.py", "physics.py", "hubbard.cpp", "hubbard.so")}, "count": len(labels), "source_labels_not_exposed_to_child": True, "quality": None}
        if runtime["failure"] is None:
            content = evaluator.read_output(output_path, settings["prediction_bytes"])
            predictions = evaluator.parse_predictions(content, len(labels))
            report["quality"] = evaluator.score_predictions(predictions, labels, inputs["family"], settings)
            (destination / "predictions.json").write_text(content)
        (destination / "report.json").write_text(json.dumps(report, indent=2))
        print(json.dumps(report, indent=2), flush=True)


if __name__ == "__main__":
    main()
