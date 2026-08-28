import argparse
import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import numpy as np


PRIVATE = Path(__file__).resolve().parent
ROOT = PRIVATE.parent
sys.path.insert(0, str(ROOT / "participant" / "workspace"))
from solve import solve as weak_solve, unpack


def errors(request, prediction, reference):
    expected_green = unpack(reference["G_retarded"])
    expected_sigma = unpack(reference["Sigma_retarded"])
    green = unpack(prediction["G_retarded"])
    sigma = unpack(prediction["Sigma_retarded"])
    if green.shape != expected_green.shape or sigma.shape != expected_sigma.shape:
        raise ValueError("incorrect output shape")
    if not np.isfinite(green).all() or not np.isfinite(sigma).all():
        raise ValueError("non-finite output")
    dimension = green.shape[-1]
    mask = ~np.eye(dimension, dtype=bool)
    spectral = -(green - green.conj().transpose(0, 2, 1)) / (2j * np.pi)
    eigenvalues = np.linalg.eigvalsh(spectral)
    denominator = max(float(np.linalg.norm(expected_green)), 1e-12)
    full = np.linalg.norm(green - expected_green) / denominator
    coherence = np.linalg.norm((green - expected_green)[:, mask]) / max(np.linalg.norm(expected_green[:, mask]), denominator * 0.05)
    self_energy = np.linalg.norm(sigma - expected_sigma) / max(np.linalg.norm(expected_sigma), denominator * 0.03)
    causal = np.linalg.norm(np.minimum(eigenvalues, 0)) / max(np.linalg.norm(eigenvalues), 1e-12)
    points = np.asarray(request["omega"]) + 1j * request["eta"]
    consistency = np.linalg.norm(sigma - (points[:, None, None] * np.eye(dimension) - unpack(request["h0"]) - np.linalg.inv(green))) / max(np.linalg.norm(expected_sigma), 1e-10)
    return {"propagator": float(full), "coherence": float(coherence), "self_energy": float(self_energy), "causality": float(causal), "dyson_consistency": float(consistency)}


def score_case(request, prediction, reference):
    actual = errors(request, prediction, reference)
    weak = errors(request, weak_solve(request), reference)
    scores = {}
    for component in ["propagator", "coherence", "self_energy"]:
        scale = max(0.035, weak[component] / 4)
        scores[component] = float(1 / (1 + (actual[component] / scale) ** 2))
    core = float(3 / sum(1 / max(value, 1e-15) for value in scores.values()))
    core *= float(1 / (1 + (actual["causality"] / 0.015) ** 2 + (actual["dyson_consistency"] / 0.01) ** 2))
    return core, scores, actual, weak


def invoke(submission, request, temporary, timeout):
    input_path = temporary / "request.json"
    output_path = temporary / "result.json"
    input_path.write_text(json.dumps(request))
    command = [sys.executable, str(submission), "--input", str(input_path), "--output", str(output_path)]
    environment = os.environ.copy()
    environment.update(OMP_NUM_THREADS="1", OPENBLAS_NUM_THREADS="1", MKL_NUM_THREADS="1", NUMBA_NUM_THREADS="1")
    wrapper = environment.get("ALPS_EVAL_WRAPPER")
    if wrapper:
        command = [sys.executable, wrapper, "--participant", str(ROOT / "participant"), "--submission", str(submission),
                   "--work", str(temporary), "--timeout", str(timeout), "--"] + command
    result = subprocess.run(command, cwd=temporary, env=environment, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=timeout + 10)
    if result.returncode:
        raise RuntimeError(f"exit {result.returncode}: {result.stderr.decode(errors='replace')[-1200:]}")
    return json.loads(output_path.read_text())


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--submission")
    parser.add_argument("--split", default="core")
    parser.add_argument("--report", required=True)
    parser.add_argument("--reference", action="store_true")
    arguments = parser.parse_args()
    manifest = json.loads((PRIVATE / "challenge_pool" / f"{arguments.split}.json").read_text())
    results = []
    for entry in manifest:
        request = json.loads((PRIVATE / entry["input"]).read_text())
        reference = json.loads((PRIVATE / entry["expected"]).read_text())
        started = time.monotonic()
        try:
            with tempfile.TemporaryDirectory(prefix="alps-cont-") as directory:
                prediction = reference if arguments.reference else invoke(Path(arguments.submission).resolve(), request, Path(directory), 120)
                score, components, error, weak = score_case(request, prediction, reference)
                record = {"id": entry["id"], "family": entry["family"], "score": score, "components": components, "errors": error, "weak_errors": weak}
                usage_file = Path(directory) / "_resource.json"
                if usage_file.exists():
                    record["resources"] = json.loads(usage_file.read_text())
                    if record["resources"]["max_rss_kib"] > 2 * 1024 ** 2:
                        record["score"] = 0.0
                        record["error"] = "resident memory exceeded 2 GiB"
        except Exception as exception:
            record = {"id": entry["id"], "family": entry["family"], "score": 0.0, "error": str(exception)}
        record["seconds"] = time.monotonic() - started
        results.append(record)
        print(json.dumps(record), flush=True)
    families = {family: float(np.mean([record["score"] for record in results if record["family"] == family])) for family in sorted({record["family"] for record in results})}
    report = {"split": arguments.split, "mean_core_score": float(np.mean([record["score"] for record in results])),
              "worst_family_score": min(families.values()), "families": families, "cases": results,
              "seconds": sum(record["seconds"] for record in results), "sandboxed": bool(os.environ.get("ALPS_EVAL_WRAPPER")), "stored_reference_check": arguments.reference}
    Path(arguments.report).write_text(json.dumps(report, indent=2))
    print(json.dumps({key: value for key, value in report.items() if key != "cases"}), flush=True)


if __name__ == "__main__":
    main()
