from __future__ import annotations

import argparse
import hashlib
import io
import json
import sys
import zipfile
from pathlib import Path

import numpy as np

sys.dont_write_bytecode = True
PILOT = Path(__file__).resolve().parents[1]
PAPER = PILOT.parents[1]
sys.path.insert(0, str(PAPER / "research"))

from isolation import run_submission
from metrics import failure_metrics, load_npz, measure, summarize


def unpack_answer(payload, expected_shapes):
    budget = 1024 * 1024 + 16 * sum(int(np.prod(shape)) for shape in expected_shapes.values())
    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        if {entry.filename for entry in archive.infolist()} != {"increments.npy", "syndrome_history.npy"}:
            raise ValueError("Output must contain exactly increments and syndrome_history")
        if len(archive.infolist()) != 2 or sum(entry.file_size for entry in archive.infolist()) > budget:
            raise ValueError("Output exceeds the bounded NPZ schema")
        for entry in archive.infolist():
            with archive.open(entry) as stream:
                version = np.lib.format.read_magic(stream)
                if version == (1, 0):
                    shape, _, dtype = np.lib.format.read_array_header_1_0(stream)
                elif version == (2, 0):
                    shape, _, dtype = np.lib.format.read_array_header_2_0(stream)
                else:
                    raise ValueError("Unsupported NPY header version")
                if shape != expected_shapes[entry.filename[:-4]] or dtype.kind not in "biu":
                    raise ValueError("NPY header shape or dtype does not match the contract")
                if stream.tell() + int(np.prod(shape)) * dtype.itemsize != entry.file_size:
                    raise ValueError("NPY body size does not match its header")
    return load_npz(io.BytesIO(payload))


def evaluate(submission, split, cpu_budget=120):
    submission = Path(submission).resolve()
    if not (submission / "solve.py").is_file():
        raise ValueError("--submission must be a directory containing solve.py")
    pool = PILOT / "private/challenge_pool" / split
    manifest_path = pool / "manifest.json"
    manifest = json.loads(manifest_path.read_text())
    if split == "holdout" and manifest.get("generation_phase") != "post_attempt_fresh":
        raise ValueError("Holdout is reserved until fresh post-attempt generation")
    if not manifest["ready"]:
        raise ValueError("The reference corpus has not passed headroom checks")
    results = []
    for record in manifest["cases"]:
        input_path = pool / record["input"]
        truth_path = pool / record["truth"]
        for path, expected in ((input_path, record["input_sha256"]), (truth_path, record["truth_sha256"])):
            if hashlib.sha256(path.read_bytes()).hexdigest() != expected:
                raise ValueError(f"Corpus checksum mismatch: {path.name}")
        case = load_npz(input_path)
        truth = load_npz(truth_path)
        execution = run_submission(
            submission, PILOT / "participant", input_path,
            output_suffix=".npz", timeout=max(60, 3 * cpu_budget), memory_mb=1536,
        )
        payload = execution.pop("answer_bytes")
        cpu_known = "user_seconds" in execution and "system_seconds" in execution
        cpu_seconds = execution.get("user_seconds", 0.0) + execution.get("system_seconds", 0.0)
        result = {
            "case_id": record["case_id"], "family": record["family"],
            "runtime_seconds": cpu_seconds, "cpu_time_known": cpu_known,
            "wall_seconds": execution["elapsed_seconds"], "execution": execution,
            "reference_build_seconds": record["build_seconds"],
        }
        try:
            if payload is None:
                raise ValueError("No successful output: crash, timeout, or missing answer")
            if not cpu_known or cpu_seconds > cpu_budget:
                raise ValueError("Missing CPU accounting or CPU budget exceeded")
            shots, rounds, num_checks = case["readout"].shape
            expected_shapes = {
                "increments": (shots, rounds, case["checks"].shape[1]),
                "syndrome_history": (shots, rounds, num_checks),
            }
            answer = unpack_answer(payload, expected_shapes)
            result["metrics"] = measure(case, truth, answer)
            result["status"] = "ok"
        except (ValueError, KeyError, OSError, EOFError, zipfile.BadZipFile) as error:
            result["metrics"] = failure_metrics(record["shots"])
            result["status"] = "invalid"
            result["error"] = str(error)
        results.append(result)
    report = summarize(results, manifest["anchors"])
    report.update({
        "split": split,
        "submission": str(submission),
        "cases": results,
        "runtime_seconds": sum(result["runtime_seconds"] for result in results),
        "wall_seconds": sum(result["wall_seconds"] for result in results),
        "runtime_basis": "user_seconds + system_seconds; source reference uses process_time",
        "cpu_budget_seconds_per_case": cpu_budget,
        "wall_timeout_seconds_per_case": max(60, 3 * cpu_budget),
        "manifest_sha256": hashlib.sha256(manifest_path.read_bytes()).hexdigest(),
        "isolation_helper_sha256": hashlib.sha256((PAPER / "research/isolation.py").read_bytes()).hexdigest(),
        "isolation": "research/isolation.py run_submission; bwrap; no private mounts",
        "normalization": "unclipped (family mean quality - weak) / (reference - weak); equal core/family weights",
    })
    return report


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--submission", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--split", choices=("pilot", "challenge", "holdout"), default="pilot")
    arguments = parser.parse_args()
    report = evaluate(arguments.submission, arguments.split)
    arguments.report.parent.mkdir(parents=True, exist_ok=True)
    arguments.report.write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
    print(json.dumps({name: report[name] for name in ("mean_core", "worst_family", "runtime_seconds")}))


if __name__ == "__main__":
    main()
