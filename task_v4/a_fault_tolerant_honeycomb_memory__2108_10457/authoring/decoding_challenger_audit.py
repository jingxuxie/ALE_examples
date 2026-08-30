import argparse
import importlib.util
import json
import os
from pathlib import Path
import sys


os.environ["OPENBLAS_NUM_THREADS"] = "1"
ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "authoring"), str(ROOT / "authoring/deps"), str(ROOT / "authoring/upstream/src")]
import numpy as np
from build_decoding import write_case


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("submission", type=Path, nargs="?")
    parser.add_argument("--generate-only", action="store_true")
    arguments = parser.parse_args()
    destination = ROOT / "concept_1/adversary/broad_native"
    destination.mkdir(parents=True, exist_ok=True)
    manifest_path = destination / "manifest.json"
    if not manifest_path.exists():
        manifest = []
        families = [("em3", "EM3_v2", [0.012, 0.015, 0.016]),
                    ("sd6", "SD6", [0.0015, 0.0019, 0.0022]),
                    ("si1000", "SI1000", [0.0009, 0.00115, 0.0013])]
        geometries = [(12, 18, 48, 2), (16, 24, 48, 1), (8, 12, 96, 0), (12, 24, 48, 1)]
        for family_index, (family, style, probabilities) in enumerate(families):
            for geometry_index, (width, height, rounds, probability_index) in enumerate(geometries):
                identifier = f"{family}_stress_{geometry_index}"
                configuration = {"data_width": width, "data_height": height, "sub_rounds": rounds,
                                 "style": style, "obs": "H" if geometry_index % 2 == 0 else "V",
                                 "noise": probabilities[probability_index]}
                baseline, errors = write_case(destination / "requests" / identifier, configuration,
                                              701137 + family_index * 1973 + geometry_index * 6173,
                                              8192, destination / "labels")
                (destination / "stock_baseline").mkdir(exist_ok=True)
                np.save(destination / "stock_baseline" / (identifier + ".npy"), baseline, allow_pickle=False)
                manifest.append({"id": identifier, "family": family, "shots": 8192,
                                 "baseline_errors": errors, "configuration": configuration})
                print("generated", identifier, errors, flush=True)
        manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")
    manifest = json.loads(manifest_path.read_text())
    if arguments.generate_only:
        return
    if arguments.submission is None:
        parser.error("submission is required unless --generate-only")
    specification = importlib.util.spec_from_file_location("decoding_evaluation", ROOT / "concept_1/evaluator/evaluate.py")
    evaluator = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(evaluator)
    evaluator.HIDDEN = destination
    submission = evaluator.verify_submission(arguments.submission)
    records = []
    for case in manifest:
        try:
            prediction, elapsed = evaluator.run_case(submission, case)
            truth = np.load(destination / "labels" / (case["id"] + ".npy"), allow_pickle=False)
            errors = int(np.count_nonzero(prediction != truth))
            (destination / "candidate_predictions").mkdir(exist_ok=True)
            np.save(destination / "candidate_predictions" / (case["id"] + ".npy"), prediction, allow_pickle=False)
            record = case | {"valid": True, "errors": errors, "stock_failure_ratio": errors / max(1, case["baseline_errors"]),
                             "seconds": elapsed}
        except Exception as error:
            record = case | {"valid": False, "reason": str(error)}
        records.append(record)
        report = {"cases": records, "complete": len(records) == len(manifest),
                  "interpretation": "Private source-native audit of larger, longer, and anisotropic memories. Original generation1 targets and samples are unchanged. A scientific failure must be judged with counts and resource reproducibility, not one noisy ratio."}
        (destination / "candidate_report.json").write_text(json.dumps(report, indent=2) + "\n")
        print(json.dumps(record), flush=True)


if __name__ == "__main__":
    main()
