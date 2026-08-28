import argparse
import json
import os
from pathlib import Path
import shutil
import statistics
import subprocess
import sys
import tempfile
import time

from metrics import compare, relative_score

ROOT = Path(__file__).resolve().parents[1]
PARTICIPANT = ROOT / "participant"
CHALLENGE = ROOT / "private/challenge_pool"
for candidate in (ROOT.parents[1] / "research", ROOT.parents[1] / "output/research"):
    if (candidate / "isolation.py").exists():
        sys.path.insert(0, str(candidate))
        break
from isolation import run_submission


def load(path):
    return json.loads(Path(path).read_text())


def save(path, value):
    Path(path).write_text(json.dumps(value, indent=2) + "\n")


def run_case(submission, name, cpu_budget):
    with tempfile.TemporaryDirectory(prefix="pilot04-submission-") as temporary:
        staged = Path(temporary) / "submission"
        shutil.copytree(submission, staged, symlinks=True, ignore=shutil.ignore_patterns("__pycache__", ".git", ".codex", ".agents"))
        result = run_submission(staged, PARTICIPANT, CHALLENGE / f"{name}.json",
                                output_suffix=".json", timeout=max(60.0, 3 * cpu_budget), memory_mb=1536,
                                cpu_limit=cpu_budget, submission_aliases=[submission])
    result["cpu_seconds"] = result.get("user_seconds", 0.0) + result.get("system_seconds", 0.0)
    result["cpu_exhausted"] = (result["cpu_seconds"] > cpu_budget or
                               (result["returncode"] in (137, 152, -9, -24)
                                and result["cpu_seconds"] >= cpu_budget * 0.9))
    answer_bytes = result.pop("answer_bytes")
    expected = load(CHALLENGE / f"{name}.answer.json")
    if answer_bytes is None:
        result.update(quality=0.0, exact=False)
    else:
        try:
            result.update(compare(json.loads(answer_bytes), expected))
        except (ValueError, UnicodeDecodeError, TypeError) as error:
            result.update(quality=0.0, exact=False, error=str(error))
    return result


def time_reference(name, cpu_budget):
    times = []
    wall_times = []
    for repetition in range(3):
        with tempfile.TemporaryDirectory(prefix="pilot04-reference-") as temporary:
            answer_path = Path(temporary) / "answer.json"
            usage_path = Path(temporary) / "usage.json"
            command = ["/usr/bin/time", "-f", '{"user_seconds":%U,"system_seconds":%S}',
                       "-o", str(usage_path), "/usr/bin/python3", str(ROOT / "private/reference/official.py"),
                       "--input", str(CHALLENGE / f"{name}.json"), "--output", str(answer_path)]
            environment = dict(os.environ)
            for key in ("PYTHONPATH", "PYTHONHOME"):
                environment.pop(key, None)
            environment.update(OMP_NUM_THREADS="1", OPENBLAS_NUM_THREADS="1", MKL_NUM_THREADS="1")
            started = time.perf_counter()
            subprocess.run(command, check=True, capture_output=True, env=environment,
                           timeout=max(60.0, 3 * cpu_budget))
            wall_times.append(time.perf_counter() - started)
            usage = load(usage_path)
            times.append(usage["user_seconds"] + usage["system_seconds"])
            result = compare(load(answer_path), load(CHALLENGE / f"{name}.answer.json"))
            if not result["exact"]:
                raise AssertionError("Reference CLI disagrees with stored oracle")
    return statistics.median(times), times, wall_times


def calibrate():
    manifest = load(CHALLENGE / "manifest.json")
    timeout = manifest["cpu_budget_seconds"]
    cases = []
    for case in manifest["performance"]:
        name = case["case_id"]
        reference_time, samples, wall_samples = time_reference(name, timeout)
        weak = run_case(PARTICIPANT / "workspace", name, timeout)
        baseline = {"case_id": name, "reference_seconds": reference_time,
                    "reference_samples": samples, "reference_wall_samples": wall_samples,
                    "weak_seconds": timeout if weak["cpu_exhausted"] else weak["cpu_seconds"],
                    "weak_wall_seconds": weak["elapsed_seconds"],
                    "weak_quality": weak["quality"], "weak_timeout": weak["timeout"],
                    "weak_cpu_exhausted": weak["cpu_exhausted"],
                    "weak_returncode": weak["returncode"], "weak_stderr": weak["stderr"],
                    "weak_max_rss_kb": weak.get("max_rss_kb"), "statistics": case}
        if baseline["weak_seconds"] <= reference_time:
            raise AssertionError(f"Weak baseline faster than reference: {name}")
        if weak["timeout"]:
            raise AssertionError(f"Infrastructure wall timeout; recalibrate rather than score: {weak}")
        if not weak["cpu_exhausted"] and weak["returncode"] != 0:
            raise AssertionError(f"Weak failed for infrastructure reasons: {weak}")
        cases.append(baseline)
        print(json.dumps(baseline), flush=True)
    for family in ("surface", "nongeometric_hgp"):
        if not any(case["weak_cpu_exhausted"] and case["statistics"]["provenance"]["family"] == family
                   for case in cases):
            raise AssertionError(f"Anti-compression test not met for {family}")
    audits = [run_case(PARTICIPANT / "workspace", case["case_id"], timeout)
              for case in manifest["audits"]]
    if not all(case["exact"] for case in audits):
        raise AssertionError(("Isolated semantic audits failed", audits))
    result = {"cpu_budget_seconds": timeout, "wall_timeout_seconds": max(60.0, 3 * timeout),
              "timing_basis": "user_seconds + system_seconds", "cases": cases, "weak_audits": audits,
              "anti_compression_passed": True, "reference_normalized_score": 100.0,
              "weak_normalized_score": 0.0}
    save(ROOT / "private/reference/calibration.json", result)
    return result


def evaluate(submission, split="pilot"):
    manifest = load(CHALLENGE / "manifest.json")
    calibration = load(ROOT / "private/reference/calibration.json")
    timeout = calibration["cpu_budget_seconds"]
    audit_results = [run_case(submission, case["case_id"], timeout) for case in manifest["audits"]]
    audit_quality = statistics.mean(case["quality"] for case in audit_results)
    results = []
    for baseline in calibration["cases"]:
        name = baseline["case_id"]
        result = run_case(submission, name, timeout)
        quality = result["quality"] * audit_quality
        elapsed = timeout if result["cpu_exhausted"] or result["timeout"] else max(result["cpu_seconds"], 0.01)
        score, speed = relative_score(quality, elapsed, baseline)
        results.append({"case_id": name, **result, "audit_adjusted_quality": quality,
                        "family": baseline["statistics"]["provenance"]["family"],
                        "score": score, "core_score": score / 100.0, "relative_log_speed": speed})
    mean_score = statistics.mean(result["score"] for result in results)
    return {"score": mean_score, "mean_core": mean_score / 100.0,
            "worst_family": min(result["score"] for result in results) / 100.0,
            "core_scale": "weak=0, reference=1; original score field remains percent units",
            "split": split, "split_policy": "shared_initial_pool",
            "audit_quality": audit_quality, "audits": audit_results, "cases": results,
            "all_exact": all(result["exact"] for result in audit_results + results)}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--submission", type=Path)
    parser.add_argument("--calibrate", action="store_true")
    parser.add_argument("--output", "--report", dest="output", type=Path)
    parser.add_argument("--split", choices=("pilot", "challenge", "holdout"), default="pilot")
    args = parser.parse_args()
    if args.calibrate:
        result = calibrate()
    elif args.submission:
        result = evaluate(args.submission.resolve(), args.split)
    else:
        parser.error("Specify --submission or --calibrate")
    if args.output:
        save(args.output, result)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
