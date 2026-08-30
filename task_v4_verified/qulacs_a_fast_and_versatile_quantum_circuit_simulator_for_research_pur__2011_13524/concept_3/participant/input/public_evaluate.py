import argparse
import json
import os
from pathlib import Path
import resource
import selectors
import shutil
import signal
import subprocess
import sys
import tempfile
import time

import numpy as np

from simulator import BUDGET, FAMILIES, metadata, probabilities, score_estimate, validate_action, validate_estimate


INPUT = Path(__file__).resolve().parent


def child_limits():
    os.sched_setaffinity(0, {min(os.sched_getaffinity(0))})
    resource.setrlimit(resource.RLIMIT_CPU, (40, 41))
    resource.setrlimit(resource.RLIMIT_AS, (1024 ** 3, 1024 ** 3))


def run_episode(submission, episode):
    started = time.monotonic()
    result = {"id": episode["id"], "family": episode["family"], "score": 0.0, "valid": False}
    queries = 0
    shots = 0
    process = None
    try:
        with tempfile.TemporaryDirectory(prefix="public-ramsey-") as scratch:
            directory = Path(scratch)
            shutil.copytree(submission, directory, dirs_exist_ok=True, ignore=shutil.ignore_patterns("input", "__pycache__"))
            shutil.copytree(INPUT, directory / "input", ignore=shutil.ignore_patterns("__pycache__"))
            environment = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", OPENBLAS_NUM_THREADS="1", OMP_NUM_THREADS="1", MKL_NUM_THREADS="1")
            process = subprocess.Popen([sys.executable, "-u", "solution.py"], cwd=directory, env=environment,
                                       stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                                       start_new_session=True, preexec_fn=child_limits)
            selector = selectors.DefaultSelector()
            selector.register(process.stdout, selectors.EVENT_READ)
            rng = np.random.default_rng(episode["outcome_seed"])
            truth = validate_estimate({"type": "estimate", "parameters": episode["parameters"]})
            message = metadata()
            buffered = b""
            try:
                while True:
                    process.stdin.write((json.dumps(message) + "\n").encode())
                    process.stdin.flush()
                    while b"\n" not in buffered:
                        remaining = 45 - (time.monotonic() - started)
                        if remaining <= 0 or not selector.select(remaining):
                            raise ValueError("public episode timeout")
                        chunk = os.read(process.stdout.fileno(), 16385)
                        if not chunk:
                            raise ValueError("child exited without a response")
                        buffered += chunk
                        if len(buffered) > 16384:
                            raise ValueError("response line too long")
                    line, buffered = buffered.split(b"\n", 1)
                    if buffered:
                        raise ValueError("multiple responses")
                    response = json.loads(line)
                    if response.get("type") == "estimate":
                        estimate = validate_estimate(response)
                        process.stdin.close()
                        process.wait(timeout=min(1, max(0.01, 45 - (time.monotonic() - started))))
                        if process.returncode != 0:
                            raise ValueError("nonzero child exit")
                        result.update(score_estimate(truth, estimate))
                        result.update(valid=True, reason="public smoke test only")
                        break
                    action = validate_action(response)
                    if queries >= BUDGET["queries"] or shots + action["shots"] > BUDGET["shots"]:
                        raise ValueError("query or shot budget exceeded")
                    positive = int(rng.binomial(action["shots"], probabilities(truth, [action])[0]))
                    queries += 1
                    shots += action["shots"]
                    message = {"type": "observation", "action": action, "counts": [positive, action["shots"] - positive],
                               "remaining": {"queries": 48 - queries, "shots": 6144 - shots}}
            finally:
                selector.close()
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                process.wait()
                if not process.stdin.closed:
                    process.stdin.close()
                process.stdout.close()
    except (ValueError, OSError, TypeError, AttributeError, subprocess.TimeoutExpired) as error:
        result["reason"] = str(error)
    result.update(queries=queries, shots=shots, runtime_seconds=time.monotonic() - started)
    return result


def main():
    parser = argparse.ArgumentParser(description="Public-only smoke test; never reads private evaluator state")
    parser.add_argument("--submission", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    arguments = parser.parse_args()
    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    tempfile.tempdir = str(arguments.output.parent.resolve())
    started = time.monotonic()
    episodes = json.loads((INPUT / "public_examples.json").read_text())["episodes"]
    results = [run_episode(arguments.submission.resolve(), episode) for episode in episodes]
    family_means = {family: float(np.mean([result["score"] for result in results if result["family"] == family])) for family in FAMILIES}
    target = json.loads((INPUT / "OBJECTIVE.json").read_text())["target"]
    mean = float(np.mean([result["score"] for result in results]))
    worst = min(family_means.values())
    passed = all(result["valid"] for result in results) and mean >= target["mean"] and worst >= target["worst_family"]
    report = {"public": True, "episodes": results, "mean": mean, "worst_family": worst, "family_means": family_means,
              "target": target, "runtime_seconds": time.monotonic() - started, "passed": passed,
              "reason": "Public examples only; not hidden evaluation or a security sandbox"}
    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    arguments.output.write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
    print(json.dumps({key: report[key] for key in ("mean", "worst_family", "runtime_seconds", "passed", "reason")}))


if __name__ == "__main__":
    main()
