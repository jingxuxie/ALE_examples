"""Continuous component scoring and integration with the common sandbox helper."""

import argparse
import importlib.util
import json
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parent
KEYS = ("reciprocal_fc3", "coupling_strength")


def component_error(actual, reference):
    residual = np.asarray(actual) - reference
    numerator = np.mean(np.abs(residual.reshape(len(reference), -1)) ** 2, axis=1)
    denominator = np.mean(np.abs(reference.reshape(len(reference), -1)) ** 2, axis=1)
    floor = max(float(np.mean(denominator)) * 1e-24, np.finfo(float).tiny)
    return float(np.sqrt(np.mean(numerator / np.maximum(denominator, floor))))


def score_case(actual, reference, baseline, case, input_data):
    scores = {}
    triplet_count = len(input_data["qpoints"])
    primitive_count = len(input_data["p2s_map"])
    shapes = {
        "reciprocal_fc3": (triplet_count,) + (primitive_count,) * 3 + (3,) * 3,
        "coupling_strength": (triplet_count,) + (3 * primitive_count,) * 3,
    }
    for key in case.get("keys", KEYS):
        scores[key] = 0.0
        if key not in actual or key not in shapes:
            continue
        try:
            value = np.asarray(actual[key])
        except (ValueError, TypeError):
            continue
        if value.shape != shapes[key] or not np.issubdtype(value.dtype, np.number):
            continue
        if not np.isfinite(value).all():
            continue
        if key == "coupling_strength" and (np.iscomplexobj(value) or np.any(value < 0)):
            continue
        weak_error = component_error(baseline[key], reference[key])
        if not np.isfinite(weak_error) or weak_error <= 0:
            raise ValueError(f"Invalid measured baseline error for {case.get('id')}: {key}")
        with np.errstate(over="ignore", invalid="ignore"):
            error = component_error(value, reference[key])
        if np.isfinite(error):
            scores[key] = float(1.0 / (1.0 + error / weak_error))
    return scores


def load_archive(path):
    with np.load(path, allow_pickle=False) as archive:
        return dict(archive)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--submission", type=Path, default=ROOT.parent / "participant/workspace/solve.py")
    parser.add_argument("--manifest", type=Path, default=ROOT / "challenge_pool/manifest.json")
    parser.add_argument("--split", choices=("heldout", "pool", "all"), default="heldout")
    parser.add_argument("--output", type=Path, default=ROOT / "reference/evaluation.json")
    arguments = parser.parse_args()
    helper_path = ROOT.parents[2] / "author/evaluation.py"
    specification = importlib.util.spec_from_file_location("common_evaluation", helper_path)
    helper = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(helper)
    cases = json.loads(arguments.manifest.read_text())
    reports = []
    for case in cases:
        if arguments.split != "all" and case["split"] != arguments.split:
            continue
        output_directory = arguments.output.parent / arguments.output.stem / case["id"]
        output_directory.mkdir(parents=True, exist_ok=True)
        run = helper.sandbox_run(
            arguments.submission.resolve(), (ROOT / case["input"]).resolve(),
            output_directory.resolve(), ROOT.parent / "participant",
            timeout=case.get("timeout", 180), memory_mb=case.get("memory_mb", 8192),
        )
        scores = {key: 0.0 for key in case["keys"]}
        failure = None
        if run.get("status") == "ok" and run.get("output_path") and Path(run["output_path"]).is_file():
            try:
                scores = score_case(
                    load_archive(run["output_path"]), load_archive(ROOT / case["reference"]),
                    load_archive(ROOT / case["baseline"]), case, load_archive(ROOT / case["input"]),
                )
            except (ValueError, OSError, KeyError, TypeError) as error:
                failure = str(error)
        reports.append({"id": case["id"], "family": case["family"], "split": case["split"],
                        "run": run, "scores": scores, "score_error": failure})
        print(json.dumps({"id": case["id"], "status": run["status"], "scores": scores}), flush=True)
    if not reports:
        raise ValueError("No cases selected")
    result = {"cases": reports, "components": {
        key: float(np.mean([report["scores"][key] for report in reports])) for key in KEYS
    }}
    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    arguments.output.write_text(json.dumps(result, indent=2, default=str) + "\n")


if __name__ == "__main__":
    main()
