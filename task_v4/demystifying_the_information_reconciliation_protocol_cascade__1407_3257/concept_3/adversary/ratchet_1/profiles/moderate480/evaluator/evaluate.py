"""Private parent evaluator; never imports or executes policy code in-process."""

import argparse
import collections
from concurrent.futures import ProcessPoolExecutor
import hashlib
import json
import math
import os
from pathlib import Path
import resource
import select
import shutil
import signal
import subprocess
import sys
import time


ROOT = Path(__file__).resolve().parents[1]
PUBLIC = ROOT / "participant" / "input"
sys.path.insert(0, str(PUBLIC))
from simulator import CONTRACT, Device, ProtocolError


class PolicyFailure(RuntimeError):
    pass


def sandbox_command(policy):
    bubblewrap = shutil.which("bwrap")
    if not bubblewrap:
        raise RuntimeError("bubblewrap is required; there is no unsandboxed fallback")
    policy = Path(policy).resolve(strict=True)
    if not policy.is_file() or policy.stat().st_size > 131072:
        raise RuntimeError("submission must be one Python file, at most 128 KiB")
    if any(path.is_symlink() for path in PUBLIC.rglob("*")):
        raise RuntimeError("public input contains a symlink")
    command = [
        bubblewrap, "--unshare-user", "--unshare-pid", "--unshare-net",
        "--unshare-ipc", "--unshare-uts", "--die-with-parent", "--new-session",
        "--cap-drop", "ALL", "--clearenv",
    ]
    for directory in ("/usr", "/bin", "/lib", "/lib64"):
        if Path(directory).exists():
            command.extend(("--ro-bind", directory, directory))
    command.extend((
        "--tmpfs", "/tmp", "--dir", "/submission",
        "--ro-bind", str(PUBLIC), "/task",
        "--ro-bind", str(policy), "/submission/policy.py",
        "--chdir", "/submission", "--setenv", "PATH", "/usr/bin:/bin",
        "/usr/bin/python3", "-I", "-B", "-u", "-c",
        "import os; os.write(1,b'{\"sandbox_ready\":true}\\n'); os.execv('/usr/bin/python3',['python3','-I','-B','-u','/submission/policy.py'])",
    ))
    return command


def process_limits():
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    memory = CONTRACT["memory_mib"] * 1024 * 1024
    resource.setrlimit(resource.RLIMIT_AS, (memory, memory))
    resource.setrlimit(resource.RLIMIT_CPU, (CONTRACT["cpu_seconds"], CONTRACT["cpu_seconds"]))
    resource.setrlimit(resource.RLIMIT_FSIZE, (1048576, 1048576))
    resource.setrlimit(resource.RLIMIT_NOFILE, (64, 64))


class PolicyProcess:
    def __init__(self, policy, wall_seconds=None):
        self.command = sandbox_command(policy)
        self.wall_seconds = CONTRACT["wall_seconds"] if wall_seconds is None else wall_seconds
        self.buffer = bytearray()
        self.process = None

    def __enter__(self):
        self.deadline = time.monotonic() + 120
        self.process = subprocess.Popen(
            self.command,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            close_fds=True,
            start_new_session=True,
            preexec_fn=process_limits,
            env={"PATH": "/usr/bin:/bin"},
        )
        os.set_blocking(self.process.stdin.fileno(), False)
        try:
            if self.receive() != {"sandbox_ready": True}:
                raise PolicyFailure("sandbox initialization failed")
        except Exception:
            self.__exit__(None, None, None)
            raise
        self.deadline = time.monotonic() + self.wall_seconds
        return self

    def send(self, message):
        encoded = (json.dumps(message, separators=(",", ":")) + "\n").encode()
        offset = 0
        try:
            while offset < len(encoded):
                remaining = self.deadline - time.monotonic()
                if remaining <= 0:
                    raise PolicyFailure("wall time exceeded")
                _, writable, _ = select.select([], [self.process.stdin], [], remaining)
                if not writable:
                    raise PolicyFailure("wall time exceeded")
                try:
                    offset += os.write(self.process.stdin.fileno(), encoded[offset:offset + 4096])
                except BlockingIOError:
                    continue
        except (BrokenPipeError, OSError) as error:
            raise PolicyFailure("policy closed input") from error

    def receive(self):
        while True:
            separator = self.buffer.find(b"\n")
            if separator >= 0:
                if separator > CONTRACT["line_bytes"]:
                    raise PolicyFailure("oversized protocol line")
                encoded = bytes(self.buffer[:separator])
                del self.buffer[:separator + 1]
                try:
                    return json.loads(encoded)
                except (ValueError, UnicodeError, RecursionError) as error:
                    raise PolicyFailure("invalid JSON") from error
            if len(self.buffer) > CONTRACT["line_bytes"]:
                raise PolicyFailure("oversized protocol line")
            remaining = self.deadline - time.monotonic()
            if remaining <= 0:
                raise PolicyFailure("wall time exceeded")
            readable, _, _ = select.select([self.process.stdout], [], [], remaining)
            if not readable:
                raise PolicyFailure("wall time exceeded")
            chunk = os.read(self.process.stdout.fileno(), CONTRACT["line_bytes"] + 1)
            if not chunk:
                raise PolicyFailure("policy exited before classification")
            self.buffer.extend(chunk)

    def __exit__(self, exception_type, exception, traceback):
        if self.process is None:
            return
        try:
            os.killpg(self.process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        self.process.wait(timeout=120)
        self.process.stdin.close()
        self.process.stdout.close()


def run_case(policy, case, wall_seconds=None):
    started = time.monotonic()
    device = Device(case["family"], case["contamination_denominator"], case["seed"])
    prediction = None
    failure = None
    try:
        with PolicyProcess(policy, wall_seconds) as process:
            process.send(device.hello())
            for operation_index in range(CONTRACT["frames"] + CONTRACT["parity_queries"] + 1):
                request = process.receive()
                response = device.handle(request)
                if request["op"] == "guess":
                    prediction = request["family"]
                    try:
                        process.send(response)
                    except PolicyFailure:
                        pass
                    break
                process.send(response)
            if prediction is None:
                raise PolicyFailure("operation budget exceeded")
    except (PolicyFailure, ProtocolError, OSError, subprocess.SubprocessError, RuntimeError) as error:
        failure = str(error)
    return {
        "correct": failure is None and prediction == case["family"],
        "prediction": prediction,
        "failure": failure,
        "frames": device.frames,
        "queries": device.queries,
        "elapsed_seconds": time.monotonic() - started,
    }


def hidden_cases():
    manifest = json.loads((ROOT / "evaluator" / "hidden" / "manifest.json").read_text())
    if manifest["episodes_per_cell"] != CONTRACT["hidden_episodes_per_cell"]:
        raise RuntimeError("hidden suite size differs from frozen contract")
    cases = []
    for family in CONTRACT["families"]:
        for denominator in CONTRACT["contamination_denominators"]:
            for replicate in range(manifest["episodes_per_cell"]):
                material = f'{manifest["root_seed"]}:{family}:{denominator}:{replicate}'.encode()
                cases.append({
                    "family": family,
                    "contamination_denominator": denominator,
                    "seed": int.from_bytes(hashlib.sha256(material).digest(), "big"),
                })
    return cases


def evaluate_case(payload):
    policy, case = payload
    return case, run_case(policy, case)


def evaluate(policy, cases, suite, jobs=8):
    started = time.monotonic()
    policy = Path(policy)
    if not policy.is_file() or policy.is_symlink() or policy.stat().st_size > 131072:
        return {"core_score": 0.0, "worst_family_score": 0.0, "runtime_resource_score": 0.0,
                "passed": False, "valid": False, "target_passed": False,
                "reason": "missing, symlinked or oversized policy.py", "suite": suite,
                "episodes": 0, "correct": 0, "accuracy": 0.0, "complete_hidden_suite": False}
    counts = collections.defaultdict(lambda: {"correct": 0, "total": 0})
    failures = collections.Counter()
    total_correct = 0
    total_queries = 0
    payloads = [(policy, case) for case in cases]
    if len(cases) > 1 and jobs > 1:
        with ProcessPoolExecutor(max_workers=jobs) as executor:
            results = list(executor.map(evaluate_case, payloads))
    else:
        results = list(map(evaluate_case, payloads))
    for case, result in results:
        cell = f'{case["family"]}@{case["contamination_denominator"]}'
        counts[cell]["total"] += 1
        counts[cell]["correct"] += int(result["correct"])
        total_correct += int(result["correct"])
        total_queries += result["queries"]
        if result["failure"]:
            failures[result["failure"]] += 1
    complete = (
        suite == "hidden"
        and len(cases) == CONTRACT["target_total_episodes"]
        and len(counts) == 9
        and all(cell["total"] == CONTRACT["hidden_episodes_per_cell"] for cell in counts.values())
    )
    passed = (
        complete
        and total_correct >= CONTRACT["target_total_correct"]
        and all(cell["correct"] >= CONTRACT["target_cell_correct"] for cell in counts.values())
    )
    accuracy = total_correct / len(cases) if cases else 0.0
    standard_error = math.sqrt(accuracy * (1 - accuracy) / len(cases)) if cases else 0.0
    return {
        "mode": "E",
        "suite": suite,
        "episodes": len(cases),
        "correct": total_correct,
        "accuracy": accuracy,
        "descriptive_standard_error": standard_error,
        "core_score": accuracy,
        "worst_family_score": min((cell["correct"] / cell["total"] for cell in counts.values()), default=0.0),
        "runtime_resource_score": 1.0 - sum(failures.values()) / len(cases) if cases else 0.0,
        "passed": passed,
        "valid": True,
        "reason": "fixed target met" if passed else "accuracy, worst-cell target, or complete-suite requirement not met",
        "elapsed_seconds": time.monotonic() - started,
        "target_passed": passed,
        "complete_hidden_suite": complete,
        "cells": dict(counts),
        "protocol_failures": dict(failures),
        "mean_queries": total_queries / len(cases) if cases else 0.0,
        "contract_sha256": hashlib.sha256((PUBLIC / "contract.json").read_bytes()).hexdigest(),
        "policy_sha256": hashlib.sha256(Path(policy).read_bytes()).hexdigest() if Path(policy).is_file() else None,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--policy", type=Path, required=True)
    parser.add_argument("--dev", action="store_true")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--jobs", type=int, choices=range(1, 17), default=8)
    arguments = parser.parse_args()
    frozen_path = ROOT / "evaluator" / "frozen.json"
    if frozen_path.exists():
        frozen = json.loads(frozen_path.read_text())
        for relative, digest in frozen["sha256"].items():
            if hashlib.sha256((ROOT / relative).read_bytes()).hexdigest() != digest:
                raise RuntimeError(f"frozen evaluator or asset changed: {relative}")
    cases = json.loads((PUBLIC / "dev_cases.json").read_text()) if arguments.dev else hidden_cases()
    suite = "development" if arguments.dev else "hidden"
    if arguments.limit is not None:
        if arguments.limit < 1:
            parser.error("--limit must be positive")
        cases = cases[:arguments.limit]
        suite += "-partial"
    report = evaluate(arguments.policy, cases, suite, arguments.jobs)
    encoded = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if arguments.output:
        arguments.output.write_text(encoded)
    print(encoded, end="")


if __name__ == "__main__":
    main()
