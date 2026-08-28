"""Private evaluation runner; submissions never see reference files."""

import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import resource
import shutil
import signal
import subprocess
import sys
import time

import numpy as np


def file_hash(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def sandbox_run(submission, input_path, output_dir, participant, timeout=180,
                memory_mb=8192):
    submission = Path(submission).resolve()
    input_path = Path(input_path).resolve()
    output_dir = Path(output_dir).resolve()
    participant = Path(participant).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "result.npz"
    output_path.unlink(missing_ok=True)
    memory_path = output_dir / "resources.txt"
    command = [
        "bwrap", "--die-with-parent", "--new-session", "--unshare-net", "--unshare-pid",
        "--ro-bind", "/usr", "/usr", "--ro-bind", "/lib", "/lib",
        "--ro-bind", "/lib64", "/lib64", "--ro-bind", "/bin", "/bin",
        "--ro-bind", "/etc/alternatives", "/etc/alternatives",
        "--ro-bind", "/etc/ld.so.cache", "/etc/ld.so.cache",
        "--proc", "/proc", "--dev", "/dev", "--tmpfs", "/tmp",
        "--ro-bind", str(submission.parent), "/submission",
        "--ro-bind", str(participant), "/participant",
        "--ro-bind", str(submission.parent), str(submission.parent),
        "--ro-bind", str(participant), str(participant),
        "--ro-bind", str(input_path), "/case/input.npz",
        "--bind", str(output_dir), "/output", "--chdir", str(submission.parent),
        "--clearenv", "--setenv", "PATH", "/usr/bin:/bin",
        "--setenv", "HOME", "/tmp", "--setenv", "PYTHONNOUSERSITE", "1",
        "--setenv", "PYTHONPATH", "/participant/workspace:/participant/workspace/runtime:/submission",
        "--setenv", "OPENBLAS_NUM_THREADS", "1",
        "--setenv", "OMP_NUM_THREADS", "1",
        "--setenv", "MKL_NUM_THREADS", "1",
        "--setenv", "NUMEXPR_NUM_THREADS", "1",
        "--setenv", "VECLIB_MAXIMUM_THREADS", "1",
        "--setenv", "MPLCONFIGDIR", "/tmp/matplotlib",
        "/usr/bin/time", "-f", "%M", "-o", "/output/resources.txt",
        "/usr/bin/python3", str(submission),
        "/case/input.npz", "/output/result.npz",
    ]

    def limit_resources():
        resource.setrlimit(resource.RLIMIT_AS, (memory_mb * 1024**2,) * 2)
        resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
        resource.setrlimit(resource.RLIMIT_CPU, (int(timeout) + 3,) * 2)

    started = time.monotonic()
    process = subprocess.Popen(command, stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE, text=True,
                               start_new_session=True, preexec_fn=limit_resources)
    try:
        stdout, stderr = process.communicate(timeout=timeout)
        status = "ok" if process.returncode == 0 and output_path.is_file() else "error"
    except subprocess.TimeoutExpired:
        os.killpg(process.pid, signal.SIGKILL)
        stdout, stderr = process.communicate()
        status = "timeout"
    max_rss = None
    if memory_path.exists():
        for line in reversed(memory_path.read_text().splitlines()):
            if line.strip().isdigit():
                max_rss = int(line.strip())
                break
    return {
        "status": status, "seconds": time.monotonic() - started,
        "max_rss_kb": max_rss, "output_path": str(output_path),
        "stdout": stdout[-12000:], "stderr": stderr[-12000:],
        "returncode": process.returncode,
        "submission_sha256": file_hash(submission),
        "input_sha256": file_hash(input_path),
    }


def relative_rmse(actual, reference):
    actual = np.asarray(actual)
    reference = np.asarray(reference)
    if actual.shape != reference.shape or not np.all(np.isfinite(actual)):
        return float("inf")
    difference = np.abs(actual - reference)
    scale = max(float(np.sqrt(np.mean(np.abs(reference)**2))), 1e-12)
    return float(np.sqrt(np.mean(difference**2)) / scale)


def default_score(actual, reference, baseline, case, input_data):
    keys = case.get("keys", list(reference.files))
    scores = {}
    for key in keys:
        if key not in actual or key not in baseline:
            scores[key] = {"score": 0.0, "error": None, "baseline_error": None}
            continue
        error = relative_rmse(actual[key], reference[key])
        weak_error = relative_rmse(baseline[key], reference[key])
        if not np.isfinite(weak_error):
            raise ValueError("Nonfinite or malformed weak baseline for " + key)
        denominator = max(weak_error, case.get("error_floor", 1e-6))
        score = 1.0 / (1.0 + error / denominator)
        scores[key] = {
            "score": float(score),
            "error": float(error) if np.isfinite(error) else None,
            "baseline_error": float(weak_error) if np.isfinite(weak_error) else None,
        }
    return scores


def summarize(results):
    families = {}
    family_components = {}
    for case in results:
        families.setdefault(case["family"], []).append(case["core_score"])
        for component, record in case["components"].items():
            value = record["score"] if isinstance(record, dict) else record
            family_components.setdefault(case["family"], {}).setdefault(component, []).append(value)
    family_scores = {family: float(np.mean(scores)) for family, scores in families.items()}
    component_scores = {family: {name: float(np.mean(scores)) for name, scores in components.items()}
                        for family, components in family_components.items()}
    return {
        "mean_core": float(np.mean([case["core_score"] for case in results])) if results else 0.0,
        "worst_family": min(family_scores.values()) if family_scores else 0.0,
        "family_scores": family_scores,
        "family_component_scores": component_scores,
        "worst_family_component": min((value for components in component_scores.values() for value in components.values()), default=0.0),
        "completed_cases": sum(case["status"] == "ok" for case in results),
        "total_cases": len(results),
        "total_seconds": sum(case["seconds"] for case in results),
        "max_rss_kb": max((case.get("max_rss_kb") or 0 for case in results), default=0),
    }


def evaluate(concept, submission, split="pool", output=None, score_case=None,
             case_ids=None, stored_reference=False, participant=None, manifest_path=None):
    concept = Path(concept).resolve()
    private = concept / "private"
    manifest_path = Path(manifest_path or private / "challenge_pool" / "manifest.json")
    participant = Path(participant or concept / "participant").resolve()
    manifest = json.loads(manifest_path.read_text())
    if isinstance(manifest, dict):
        manifest = manifest["cases"]
    cases = [case for case in manifest if split == "all" or case["split"] == split]
    if case_ids:
        cases = [case for case in cases if case["id"] in case_ids]
    if not cases:
        raise ValueError("Requested evaluation contains no cases")
    submission = Path(submission).resolve()
    output = Path(output or private / "evaluation.json").resolve()
    work = output.parent / (output.stem + "_artifacts")
    score_case = score_case or default_score
    results = []
    for case in cases:
        case_dir = work / case["id"]
        case_dir.mkdir(parents=True, exist_ok=True)
        reference_path = private / case["reference"]
        baseline_path = private / case["baseline"]
        input_path = private / case["input"]
        if stored_reference:
            shutil.copyfile(reference_path, case_dir / "result.npz")
            execution = {"status": "ok", "seconds": 0.0, "max_rss_kb": 0,
                         "output_path": str(case_dir / "result.npz"),
                         "stdout": "", "stderr": "", "returncode": 0}
        else:
            execution = sandbox_run(submission, input_path, case_dir,
                                    participant,
                                    timeout=case.get("timeout", 180),
                                    memory_mb=case.get("memory_mb", 8192))
        components = {key: {"score": 0.0} for key in case.get("keys", ["core"])}
        if execution["status"] == "ok":
            try:
                with np.load(execution["output_path"], allow_pickle=False) as actual, \
                     np.load(reference_path, allow_pickle=False) as reference, \
                     np.load(baseline_path, allow_pickle=False) as baseline, \
                     np.load(input_path, allow_pickle=False) as input_data:
                    components = score_case(actual, reference, baseline, case, input_data)
            except Exception as error:
                execution["status"] = "invalid_output"
                execution["stderr"] += "\n" + repr(error)
        values = [value["score"] if isinstance(value, dict) else value
                  for value in components.values()]
        if not values or not all(np.isfinite(value) and 0 <= value <= 1 for value in values):
            raise ValueError("Scorer returned invalid component scores")
        result = dict(execution, id=case["id"], family=case["family"],
                      split=case["split"], components=components,
                      core_score=float(np.mean(values)))
        results.append(result)
        print(json.dumps({key: result[key] for key in ["id", "status", "core_score", "seconds"]}),
              flush=True)
    report = {
        "concept": concept.name, "submission": str(submission), "split": split,
        "participant": str(participant), "manifest": str(manifest_path),
        "manifest_sha256": file_hash(manifest_path),
        "execution_harness_sha256": file_hash(Path(__file__)),
        "stored_reference_self_check": stored_reference,
        "score_definition": "Mean independent component quality; each default quality = 1/(1 + relative_RMSE/max(weak_relative_RMSE,1e-6)); weak baseline 0.5, reference 1; no tolerance saturation.",
        "summary": summarize(results), "cases": results,
    }
    output.write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
    return report


def cli(concept=None, score_case=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--concept", type=Path, default=concept)
    parser.add_argument("--submission", type=Path, required=True)
    parser.add_argument("--split", default="pool")
    parser.add_argument("--output", "--report", type=Path)
    parser.add_argument("--case", action="append", dest="case_ids")
    parser.add_argument("--stored-reference", action="store_true")
    parser.add_argument("--participant", type=Path)
    parser.add_argument("--manifest", type=Path)
    args = parser.parse_args()
    result = evaluate(args.concept, args.submission, args.split, args.output,
                      score_case=score_case, case_ids=args.case_ids,
                      stored_reference=args.stored_reference,
                      participant=args.participant, manifest_path=args.manifest)
    print(json.dumps(result["summary"], indent=2))


if __name__ == "__main__":
    cli()
