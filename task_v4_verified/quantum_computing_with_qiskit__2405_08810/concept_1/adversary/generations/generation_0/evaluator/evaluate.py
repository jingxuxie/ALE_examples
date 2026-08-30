import argparse
import collections
import json
import os
from pathlib import Path
import selectors
import shutil
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "participant" / "workspace"))
sys.path.insert(0, str(ROOT.parent / "authoring"))
from phase_model import check
from sandbox import limits, sandbox_command, stop_process


def strict_json(text):
    def pairs(values):
        result = {}
        for name, value in values:
            if name in result:
                raise ValueError("duplicate JSON member")
            result[name] = value
        return result
    def nonfinite(value):
        raise ValueError("nonfinite JSON number")
    return json.loads(text, object_pairs_hook=pairs, parse_constant=nonfinite)


def receive(process, timeout):
    deadline = time.monotonic() + timeout
    response = bytearray()
    selector = selectors.DefaultSelector()
    selector.register(process.stdout, selectors.EVENT_READ)
    try:
        while time.monotonic() < deadline:
            events = selector.select(max(0, deadline - time.monotonic()))
            if not events:
                raise TimeoutError(f"{timeout}-second response deadline exceeded")
            block = os.read(process.stdout.fileno(), 65536)
            if not block:
                raise ValueError("submission exited without a complete response")
            response.extend(block)
            if len(response) > 16 * 1024**2:
                raise ValueError("response exceeds 16 MiB")
            if b"\n" in response:
                line, extra = bytes(response).split(b"\n", 1)
                if extra.strip():
                    raise ValueError("unsolicited extra response")
                return strict_json(line)
        raise TimeoutError(f"{timeout}-second response deadline exceeded")
    finally:
        selector.close()


def evaluate(submission, cases):
    submission = Path(submission).resolve(strict=True)
    if not (submission / "solution.py").is_file():
        return {"core_score": 0.0, "worst_family_score": 0.0, "resource_score": 0.0, "passed": False, "valid": False, "reason": "solution.py missing", "cases": []}
    temporary = tempfile.TemporaryDirectory(prefix="phase_compiler_")
    scratch_submission = Path(temporary.name) / "submission"
    shutil.copytree(submission, scratch_submission, symlinks=True, ignore=shutil.ignore_patterns(".git", ".agents", ".codex", "__pycache__"))
    process = subprocess.Popen(sandbox_command(ROOT / "participant", scratch_submission, ready_marker=True, writable_submission=True), stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, start_new_session=True, preexec_fn=limits(cpu_seconds=15 * len(cases) + 5), bufsize=0)
    results = []
    failure = None
    try:
        if receive(process, 90) != {"sandbox_ready": True}:
            raise RuntimeError("sandbox failed its startup handshake")
        for case in cases:
            start = time.monotonic()
            process.stdin.write((json.dumps(case["input"]) + "\n").encode())
            process.stdin.flush()
            answer = receive(process, 15)
            elapsed = time.monotonic() - start
            metrics = check(case["input"], answer)
            results.append({"id": case["id"], "family": case["family"], "seconds": elapsed, "reduction": 1 - metrics["cost"] / case["baseline"]["cost"], **metrics})
            print(json.dumps({"id": case["id"], "cost": metrics["cost"], "seconds": elapsed}), file=sys.stderr, flush=True)
    except Exception as error:
        failure = f"{type(error).__name__}: {error}"
    finally:
        stop_process(process)
        temporary.cleanup()
    grouped = collections.defaultdict(list)
    for result in results:
        grouped[result["family"]].append(result["reduction"])
    family_scores = {family: sum(values) / len(values) for family, values in grouped.items()}
    valid = failure is None and len(results) == len(cases)
    core = sum(result["reduction"] for result in results) / len(cases) if valid else 0.0
    worst = min(family_scores.values()) if valid else 0.0
    maximum_seconds = max((result["seconds"] for result in results), default=15.0)
    passed = valid and core >= 0.40 and worst >= 0.25
    reason = failure or ("all semantic, quality, family, and runtime targets met" if passed else "fixed quality or worst-family target not met")
    return {"core_score": core, "worst_family_score": worst, "resource_score": max(0.0, 1 - maximum_seconds / 15), "max_case_seconds": maximum_seconds, "passed": passed, "valid": valid, "reason": reason, "family_scores": family_scores, "cases": results}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("submission")
    parser.add_argument("--cases", type=Path, default=ROOT / "evaluator" / "hidden" / "cases.json")
    parser.add_argument("--output", type=Path)
    arguments = parser.parse_args()
    report = evaluate(arguments.submission, json.loads(arguments.cases.read_text()))
    text = json.dumps(report, indent=2, allow_nan=False) + "\n"
    if arguments.output:
        arguments.output.write_text(text)
    print(text, end="")


if __name__ == "__main__":
    main()
