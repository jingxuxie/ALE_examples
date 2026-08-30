import argparse
import collections
import json
import os
from pathlib import Path
import select
import signal
import subprocess
import sys
import time

PUBLIC = Path(__file__).resolve().parents[1] / "input"
sys.path.insert(0, str(PUBLIC))
from simulator import CONTRACT, Device


def run_episode(policy, case):
    device = Device(case["family"], case["contamination_denominator"], case["seed"])
    started = time.monotonic()
    deadline = started + CONTRACT["wall_seconds"]
    process = subprocess.Popen([sys.executable, "-I", "-B", "-u", str(Path(policy).resolve())], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, start_new_session=True)
    os.set_blocking(process.stdin.fileno(), False)
    buffer = bytearray()
    prediction = None
    failure = None

    def send(value):
        encoded = (json.dumps(value) + "\n").encode()
        offset = 0
        while offset < len(encoded):
            remaining = deadline - time.monotonic()
            if remaining <= 0 or not select.select([], [process.stdin], [], max(0, remaining))[1]:
                raise TimeoutError("wall time exceeded")
            try:
                offset += os.write(process.stdin.fileno(), encoded[offset:offset + 4096])
            except BlockingIOError:
                continue

    def receive():
        while True:
            separator = buffer.find(b"\n")
            if separator >= 0:
                if separator > CONTRACT["line_bytes"]:
                    raise ValueError("oversized protocol line")
                encoded = bytes(buffer[:separator])
                del buffer[:separator + 1]
                return json.loads(encoded)
            if len(buffer) > CONTRACT["line_bytes"]:
                raise ValueError("oversized protocol line")
            remaining = deadline - time.monotonic()
            if remaining <= 0 or not select.select([process.stdout], [], [], max(0, remaining))[0]:
                raise TimeoutError("wall time exceeded")
            chunk = os.read(process.stdout.fileno(), CONTRACT["line_bytes"] + 1)
            if not chunk:
                raise ValueError("policy exited before classification")
            buffer.extend(chunk)

    try:
        send(device.hello())
        for operation_index in range(CONTRACT["frames"] + CONTRACT["parity_queries"] + 1):
            request = receive()
            response = device.handle(request)
            send(response)
            if request["op"] == "guess":
                prediction = request["family"]
                break
        if prediction is None:
            raise ValueError("operation budget exceeded")
    except Exception as exception:
        failure = str(exception)
    finally:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        process.wait()
        process.stdin.close()
        process.stdout.close()
    return {"prediction": prediction, "correct": failure is None and prediction == case["family"], "failure": failure, "queries": device.queries, "frames": device.frames, "elapsed_seconds": time.monotonic() - started}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--policy", required=True)
    parser.add_argument("--limit", type=int)
    parser.add_argument("--output")
    arguments = parser.parse_args()
    cases = json.loads((PUBLIC / "dev_cases.json").read_text())
    if arguments.limit is not None:
        if arguments.limit < 1:
            parser.error("limit must be positive")
        cases = cases[:arguments.limit]
    cells = collections.defaultdict(lambda: {"correct": 0, "total": 0})
    failures = collections.Counter()
    for case in cases:
        result = run_episode(arguments.policy, case)
        cell = cells[f'{case["family"]}@{case["contamination_denominator"]}']
        cell["correct"] += int(result["correct"])
        cell["total"] += 1
        if result["failure"]:
            failures[result["failure"]] += 1
    correct = sum(cell["correct"] for cell in cells.values())
    report = {"suite": "public_development", "core_score": correct / len(cases), "worst_family_score": min(cell["correct"] / cell["total"] for cell in cells.values()), "episodes": len(cases), "correct": correct, "cells": dict(cells), "protocol_failures": dict(failures), "passed": False, "reason": "public development is not the hidden certification suite"}
    text = json.dumps(report, indent=2) + "\n"
    if arguments.output:
        Path(arguments.output).write_text(text)
    print(text, end="")


if __name__ == "__main__":
    main()
