import argparse
import concurrent.futures
import hashlib
import json
import os
from pathlib import Path
import resource
import selectors
import signal
import subprocess
import sys
import tempfile
import time

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "evaluator" / "hidden"))
from device_model import LOWER, UPPER, probabilities, validate_experiment


def resource_limits(config):
    resource.setrlimit(resource.RLIMIT_CPU, (config["cpu_seconds"], config["cpu_seconds"] + 1))
    memory = config["memory_mib"] * 1024 * 1024
    resource.setrlimit(resource.RLIMIT_AS, (memory, memory))
    resource.setrlimit(resource.RLIMIT_FSIZE, (8 * 1024 * 1024, 8 * 1024 * 1024))
    resource.setrlimit(resource.RLIMIT_NOFILE, (128, 128))


def sandbox_command(submission, scratch):
    command = ["bwrap", "--unshare-all", "--die-with-parent", "--new-session", "--cap-drop", "ALL"]
    for path in ("/usr", "/lib", "/lib64", "/etc/alternatives", "/etc/ld.so.cache"):
        if Path(path).exists():
            command.extend(("--ro-bind", path, path))
    command.extend(("--proc", "/proc", "--dev", "/dev", "--tmpfs", "/tmp"))
    command.extend(("--ro-bind", str(ROOT / "participant"), "/task", "--ro-bind", str(submission), "/submission", "--bind", str(scratch), "/run", "--chdir", "/submission"))
    command.extend(("--clearenv", "--setenv", "PATH", "/usr/bin:/bin", "--setenv", "HOME", "/tmp", "--setenv", "PYTHONPATH", "/task/workspace", "--setenv", "PYTHONDONTWRITEBYTECODE", "1"))
    for variable in ("OMP_NUM_THREADS", "OMP_THREAD_LIMIT", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "BLIS_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
        command.extend(("--setenv", variable, "4"))
    command.extend(("--", "/usr/bin/time", "-f", '{"user_seconds":%U,"system_seconds":%S,"peak_rss_kib":%M}', "-o", "/run/resources.json", "/usr/bin/python3", "-B", "/submission/solve.py"))
    return command


def read_message(process, selector, buffer, deadline):
    while b"\n" not in buffer:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise TimeoutError("device wall-time budget exceeded")
        if not selector.select(timeout=min(remaining, 1.0)):
            if process.poll() is not None:
                raise ValueError("controller exited without a final answer")
            continue
        chunk = os.read(process.stdout.fileno(), 65536)
        if not chunk:
            raise ValueError("controller closed stdout without a final answer")
        buffer += chunk
        if len(buffer) > 131072:
            raise ValueError("protocol line exceeds 128 KiB")
    line, buffer = buffer.split(b"\n", 1)
    message = json.loads(line.decode("utf-8"))
    if not isinstance(message, dict):
        raise ValueError("protocol messages must be JSON objects")
    return message, buffer


def evaluate_device(submission, case, config):
    started = time.monotonic()
    result = {"id": case["id"], "family": case["family"], "valid": False, "normalized_rmse": 1.0, "queries": 0}
    random = np.random.default_rng(case["noise_seed"])
    process = None
    with tempfile.TemporaryDirectory(prefix="xdiag-spectroscopy-") as temporary:
        scratch = Path(temporary)
        transcript = []
        with (scratch / "stderr.txt").open("wb") as stderr:
            try:
                process = subprocess.Popen(sandbox_command(submission, scratch), stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=stderr, bufsize=0, start_new_session=True, preexec_fn=lambda: resource_limits(config))
                selector = selectors.DefaultSelector()
                selector.register(process.stdout, selectors.EVENT_READ)
                process.stdin.write((json.dumps({"type": "start", "config": config, "device_id": case["id"]}) + "\n").encode())
                buffer = b""
                while True:
                    message, buffer = read_message(process, selector, buffer, started + config["wall_seconds"])
                    if message.get("type") == "answer":
                        if set(message) != {"type", "parameters"}:
                            raise ValueError("answer requires exactly type and parameters")
                        if not isinstance(message["parameters"], list) or any(isinstance(value, bool) or not isinstance(value, (int, float)) for value in message["parameters"]):
                            raise ValueError("parameters must be a numeric list")
                        estimate = np.asarray(message["parameters"], dtype=float)
                        if estimate.shape != LOWER.shape or not np.all(np.isfinite(estimate)):
                            raise ValueError("answer requires 20 finite parameters")
                        if np.any(estimate < LOWER) or np.any(estimate > UPPER):
                            raise ValueError("answer parameters outside public ranges")
                        error = float(np.sqrt(np.mean(((estimate - case["parameters"]) / (UPPER - LOWER)) ** 2)))
                        result.update(valid=True, normalized_rmse=error, parameters=estimate.tolist(), reason="valid bounded-budget estimate")
                        process.stdin.close()
                        try:
                            process.wait(timeout=min(2.0, max(0.1, started + config["wall_seconds"] - time.monotonic())))
                        except subprocess.TimeoutExpired:
                            pass
                        break
                    validate_experiment(message)
                    if result["queries"] >= config["query_budget"]:
                        raise ValueError("experiment query budget exceeded")
                    counts = random.multinomial(config["shots"], probabilities(case["parameters"], message))
                    result["queries"] += 1
                    response = {"type": "observation", "counts": counts.tolist(), "remaining": config["query_budget"] - result["queries"]}
                    transcript.append({"query": message, "observation": response})
                    process.stdin.write((json.dumps(response) + "\n").encode())
                selector.close()
            except Exception as error:
                result.update(valid=False, normalized_rmse=1.0, reason=f"{type(error).__name__}: {error}")
            finally:
                if process is not None and process.poll() is None:
                    os.killpg(process.pid, signal.SIGKILL)
                    process.wait()
                if process is not None:
                    result["exit_code"] = process.returncode
        result["stderr_tail"] = (scratch / "stderr.txt").read_text(errors="replace")[-3000:]
        resources = scratch / "resources.json"
        if resources.exists():
            for line in resources.read_text().splitlines():
                try:
                    result["resources"] = json.loads(line)
                except json.JSONDecodeError:
                    pass
        result["transcript"] = transcript
    result["wall_seconds"] = time.monotonic() - started
    return result


def aggregate(results, config):
    families = sorted({result["family"] for result in results})
    family_scores = {family: max(0.0, 1.0 - float(np.mean([result["normalized_rmse"] for result in results if result["family"] == family]))) for family in families}
    core_score = max(0.0, 1.0 - float(np.mean([result["normalized_rmse"] for result in results])))
    worst_score = min(family_scores.values())
    valid = all(result["valid"] for result in results)
    passed = valid and core_score >= config["target_core_score"] and worst_score >= config["target_worst_family_score"]
    return {
        "core_score": core_score, "worst_family_score": worst_score,
        "family_scores": family_scores,
        "runtime_resource_score": float(np.mean([max(0.0, 1.0 - result["wall_seconds"] / config["wall_seconds"]) for result in results])),
        "valid": valid, "passed": passed,
        "reason": "all fixed inference targets met" if passed else ("one or more invalid device interactions" if not valid else "parameter recovery below fixed overall or worst-regime target"),
        "target": {"core_score": config["target_core_score"], "worst_family_score": config["target_worst_family_score"]},
        "devices": results,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--submission", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--cases", type=Path, default=ROOT / "evaluator/hidden/devices.json")
    parser.add_argument("--jobs", type=int, default=1)
    parser.add_argument("--limit", type=int)
    arguments = parser.parse_args()
    config = json.loads((ROOT / "participant/input/config.json").read_text())
    cases = json.loads(arguments.cases.read_text())
    if arguments.limit:
        cases = cases[:arguments.limit]
    if not cases:
        raise ValueError("empty evaluation suite")
    submission = arguments.submission.resolve()
    if not (submission / "solve.py").is_file():
        results = [{"id": case["id"], "family": case["family"], "valid": False, "normalized_rmse": 1.0, "queries": 0, "wall_seconds": 0.0, "reason": "submission must contain solve.py"} for case in cases]
    else:
        with concurrent.futures.ThreadPoolExecutor(max_workers=arguments.jobs) as executor:
            results = list(executor.map(lambda case: evaluate_device(submission, case, config), cases))
    report = aggregate(results, config)
    report["suite_sha256"] = hashlib.sha256(arguments.cases.read_bytes()).hexdigest()
    report["submission_sha256"] = hashlib.sha256((submission / "solve.py").read_bytes()).hexdigest() if (submission / "solve.py").is_file() else None
    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    arguments.output.write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
    print(json.dumps({key: value for key, value in report.items() if key != "devices"}, indent=2))


if __name__ == "__main__":
    main()
