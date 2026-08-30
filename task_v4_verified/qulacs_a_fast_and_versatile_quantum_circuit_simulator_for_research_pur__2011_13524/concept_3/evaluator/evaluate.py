import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import resource
import select
import selectors
import shutil
import signal
import subprocess
import sys
import tempfile
import time

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
INPUT = ROOT / "participant" / "input"
sys.path.insert(0, str(INPUT))

from simulator import BUDGET, FAMILIES, metadata, probabilities, score_estimate, validate_action, validate_estimate


class ProtocolError(Exception):
    pass


def reject_constant(value):
    raise ValueError("non-finite JSON number: " + value)


def unique_object(pairs):
    result = {}
    for name, value in pairs:
        if name in result:
            raise ValueError("duplicate JSON key: " + name)
        result[name] = value
    return result


def parse_message(line):
    try:
        value = json.loads(line, parse_constant=reject_constant, object_pairs_hook=unique_object)
    except (ValueError, UnicodeError, RecursionError) as error:
        raise ProtocolError("malformed JSON: " + str(error)) from error
    if not isinstance(value, dict):
        raise ProtocolError("response must be a JSON object")
    return value


def limits(cpu_seconds, memory_mib):
    os.sched_setaffinity(0, {min(os.sched_getaffinity(0))})
    resource.setrlimit(resource.RLIMIT_CPU, (cpu_seconds, cpu_seconds + 1))
    resource.setrlimit(resource.RLIMIT_AS, (memory_mib * 1024 ** 2, memory_mib * 1024 ** 2))
    resource.setrlimit(resource.RLIMIT_FSIZE, (4 * 1024 ** 2, 4 * 1024 ** 2))
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    resource.setrlimit(resource.RLIMIT_NOFILE, (64, 64))


def stage_submission(submission, directory):
    if not submission.is_dir() or not (submission / "solution.py").is_file():
        raise ProtocolError("submission must be a directory containing solution.py")
    total_bytes = 0
    total_files = 0
    for source in sorted(submission.rglob("*")):
        relative = source.relative_to(submission)
        if source.is_symlink():
            raise ProtocolError("submission symlinks are not allowed")
        if "__pycache__" in relative.parts or relative.parts[0] == "input":
            continue
        if source.is_dir():
            continue
        if not source.is_file():
            raise ProtocolError("submission contains a non-regular file")
        total_bytes += source.stat().st_size
        total_files += 1
        if total_files > 128 or total_bytes > 8 * 1024 ** 2:
            raise ProtocolError("submission exceeds 128 files or 8 MiB")
        destination = directory / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, destination)
    shutil.copytree(INPUT, directory / "input", ignore=shutil.ignore_patterns("__pycache__"))


class Session:
    def __init__(self, directory, config, command):
        environment = {
            "PATH": "/usr/local/bin:/usr/bin:/bin", "HOME": str(directory),
            "TMPDIR": str(directory), "LANG": "C.UTF-8", "PYTHONHASHSEED": "0",
            "PYTHONDONTWRITEBYTECODE": "1", "OPENBLAS_NUM_THREADS": "1",
            "OMP_NUM_THREADS": "1", "MKL_NUM_THREADS": "1", "NUMEXPR_NUM_THREADS": "1",
        }
        self.process = subprocess.Popen(
            command, cwd=directory, env=environment, stdin=subprocess.PIPE,
            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, start_new_session=True,
            preexec_fn=lambda: limits(config["episode_cpu_seconds"], config["memory_mib"]),
        )
        self.selector = selectors.DefaultSelector()
        self.selector.register(self.process.stdout, selectors.EVENT_READ)
        os.set_blocking(self.process.stdout.fileno(), False)
        os.set_blocking(self.process.stdin.fileno(), False)
        self.buffer = b""
        self.deadline = time.monotonic() + config["episode_wall_seconds"]
        self.max_line = config["max_line_bytes"]

    def send(self, message):
        payload = (json.dumps(message, allow_nan=False, separators=(",", ":")) + "\n").encode()
        try:
            while payload:
                remaining = self.deadline - time.monotonic()
                if remaining <= 0 or not select.select([], [self.process.stdin], [], remaining)[1]:
                    raise ProtocolError("episode wall-time limit exceeded while sending observation")
                try:
                    written = os.write(self.process.stdin.fileno(), payload)
                    payload = payload[written:]
                except BlockingIOError:
                    continue
        except (BrokenPipeError, OSError) as error:
            raise ProtocolError("child closed input") from error

    def receive(self):
        while b"\n" not in self.buffer:
            remaining = self.deadline - time.monotonic()
            if remaining <= 0:
                raise ProtocolError("episode wall-time limit exceeded")
            ready = self.selector.select(remaining)
            if not ready:
                raise ProtocolError("episode wall-time limit exceeded")
            chunk = os.read(self.process.stdout.fileno(), self.max_line + 1)
            if not chunk:
                raise ProtocolError("child exited or returned an unterminated response")
            self.buffer += chunk
            if len(self.buffer) > self.max_line:
                raise ProtocolError("response exceeds line limit")
        line, self.buffer = self.buffer.split(b"\n", 1)
        if self.buffer:
            raise ProtocolError("multiple responses without an observation")
        return parse_message(line)

    def finish(self):
        if time.monotonic() >= self.deadline:
            raise ProtocolError("episode wall-time limit exceeded")
        self.process.stdin.close()
        remaining = max(0.01, self.deadline - time.monotonic())
        try:
            self.process.wait(timeout=remaining)
        except subprocess.TimeoutExpired as error:
            raise ProtocolError("child must exit after final estimate") from error
        if self.process.returncode != 0:
            raise ProtocolError("child returned nonzero exit status")
        try:
            extra = os.read(self.process.stdout.fileno(), self.max_line + 1)
        except BlockingIOError:
            extra = b""
        if extra:
            raise ProtocolError("extra output after final estimate")

    def close(self):
        try:
            os.killpg(self.process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        self.process.wait()
        self.selector.close()
        if not self.process.stdin.closed:
            self.process.stdin.close()
        self.process.stdout.close()


def run_episode(submission, episode, config, runner_prefix=()):
    started = time.monotonic()
    solver_started = None
    session = None
    queries = 0
    shots = 0
    result = {"id": episode["id"], "family": episode["family"], "score": 0.0, "valid": False}
    try:
        truth = validate_estimate({"type": "estimate", "parameters": episode["parameters"]})
        rng = np.random.default_rng(episode["outcome_seed"])
        with tempfile.TemporaryDirectory(prefix="ramsey-run-") as scratch:
            staged = Path(scratch) / "submission"
            directory = Path(scratch) / "work"
            staged.mkdir()
            directory.mkdir()
            stage_submission(submission, staged)
            sys.path.insert(0, str(ROOT.parent / "authoring"))
            from isolation import submission_command
            inner = [
                "/usr/bin/prlimit", "--as=" + str(config["memory_mib"] * 1024 ** 2),
                "--cpu=" + str(config["episode_cpu_seconds"]) + ":" + str(config["episode_cpu_seconds"] + 1),
                "--nofile=64:64", "--fsize=4194304:4194304", "--core=0:0", "--",
                "/usr/bin/python3", "-u", "-c",
                "import os; print('{\"type\":\"sandbox_ready\"}', flush=True); os.execv('/usr/bin/python3', ['/usr/bin/python3', '-u', 'solution.py'])",
            ]
            command = list(runner_prefix) + submission_command(staged, directory, inner)
            shutil.copytree(staged, directory, dirs_exist_ok=True)
            try:
                session = Session(directory, config, command)
                session.deadline = time.monotonic() + 90
                if session.receive() != {"type": "sandbox_ready"}:
                    raise ProtocolError("isolation startup handshake failed")
                solver_started = time.monotonic()
                session.deadline = solver_started + config["episode_wall_seconds"]
                initial = metadata()
                initial["wall_seconds"] = config["episode_wall_seconds"]
                initial["cpu_seconds"] = config["episode_cpu_seconds"]
                initial["memory_mib"] = config["memory_mib"]
                session.send(initial)
                while True:
                    message = session.receive()
                    if message.get("type") == "estimate":
                        estimate = validate_estimate(message)
                        session.finish()
                        result.update(score_estimate(truth, estimate))
                        result.update({"valid": True, "reason": "ok"})
                        break
                    action = validate_action(message)
                    if queries >= BUDGET["queries"]:
                        raise ProtocolError("query budget exceeded")
                    if shots + action["shots"] > BUDGET["shots"]:
                        raise ProtocolError("shot budget exceeded")
                    probability = float(probabilities(truth, [action])[0])
                    positive = int(rng.binomial(action["shots"], probability))
                    queries += 1
                    shots += action["shots"]
                    session.send({
                        "type": "observation", "action": action,
                        "counts": [positive, action["shots"] - positive],
                        "remaining": {"queries": BUDGET["queries"] - queries, "shots": BUDGET["shots"] - shots},
                    })
            finally:
                if session is not None:
                    session.close()
    except (ProtocolError, ValueError, TypeError, OSError, OverflowError, ImportError) as error:
        result["reason"] = str(error)
    result.update({"queries": queries, "shots": shots, "runtime_seconds": time.monotonic() - started,
                   "solver_seconds": time.monotonic() - solver_started if solver_started is not None else 0.0,
                   "infrastructure_failure": solver_started is None and session is not None})
    return result


def load_suite(public=False):
    path = INPUT / "public_examples.json" if public else ROOT / "evaluator" / "hidden" / "episodes.json"
    raw = path.read_bytes()
    suite = json.loads(raw)
    episodes = suite["episodes"]
    if len({episode["id"] for episode in episodes}) != len(episodes):
        raise ValueError("duplicate evaluator episode ids")
    for episode in episodes:
        if episode["family"] not in FAMILIES or type(episode["outcome_seed"]) is not int:
            raise ValueError("invalid evaluator suite")
        validate_estimate({"type": "estimate", "parameters": episode["parameters"]})
    if not public and (len(episodes) != 18 or any(sum(episode["family"] == family for episode in episodes) != 6 for family in FAMILIES)):
        raise ValueError("hidden suite must have exactly six episodes per family")
    return episodes, hashlib.sha256(raw).hexdigest()


def evaluate(submission, public=False, runner_prefix=()):
    started = time.monotonic()
    config = json.loads((ROOT / "evaluator" / "config.json").read_text())
    episodes, suite_hash = load_suite(public)
    results = [run_episode(Path(submission).resolve(), episode, config, runner_prefix) for episode in episodes]
    families = {
        family: float(np.mean([result["score"] for result in results if result["family"] == family]))
        for family in FAMILIES
    }
    mean_score = float(np.mean([result["score"] for result in results]))
    worst = min(families.values())
    all_valid = all(result["valid"] for result in results)
    target = config["target"]
    passed = all_valid and mean_score >= target["mean"] and worst >= target["worst_family"]
    reasons = []
    if not all_valid:
        reasons.append("one or more episodes violated protocol or resource limits")
    if mean_score < target["mean"]:
        reasons.append("mean below target")
    if worst < target["worst_family"]:
        reasons.append("worst family below target")
    return {
        "protocol": config["protocol"], "public": public, "suite_sha256": suite_hash,
        "episodes": results, "mean": mean_score, "worst_family": worst,
        "family_means": families, "runtime_seconds": time.monotonic() - started,
        "passed": passed, "reason": "; ".join(reasons) if reasons else "all thresholds met",
        "target": target, "target_status": config["target_status"],
        "isolation": "bwrap_pid_mount_network_seccomp",
        "cpu_affinity_count": 1,
        "core_score": mean_score, "worst_family_score": worst, "valid": all_valid,
        "resource_score": float(all_valid),
        "infrastructure_failures": sum(result.get("infrastructure_failure", False) for result in results),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--submission", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--public", action="store_true")
    parser.add_argument("--runner-prefix-json", default="[]")
    arguments = parser.parse_args()
    try:
        runner_prefix = json.loads(arguments.runner_prefix_json)
        if not isinstance(runner_prefix, list) or not all(isinstance(item, str) and item for item in runner_prefix):
            raise ValueError("runner prefix must be a JSON list of nonempty strings")
        report = evaluate(arguments.submission, arguments.public, runner_prefix)
    except (ValueError, OSError, KeyError) as error:
        report = {"mean": 0.0, "worst_family": 0.0, "core_score": 0.0, "worst_family_score": 0.0,
                  "valid": False, "resource_score": 0.0, "runtime_seconds": 0.0, "passed": False,
                  "reason": "evaluator setup error: " + str(error)}
    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    arguments.output.write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
    print(json.dumps({key: report[key] for key in ("mean", "worst_family", "runtime_seconds", "passed", "reason")}, allow_nan=False))


if __name__ == "__main__":
    main()
