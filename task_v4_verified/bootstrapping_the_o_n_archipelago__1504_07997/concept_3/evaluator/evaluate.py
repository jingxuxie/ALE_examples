"""Parent-held oracle with a fresh, optionally OS-sandboxed JSONL policy per case."""

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import selectors
import signal
import subprocess
import sys
import tempfile
import time

BASE = Path(__file__).resolve().parents[1]
INPUT = BASE / "participant" / "input"
sys.path.insert(0, str(INPUT))

from hidden.generator import suite
from model import BUDGET, Oracle, VERSION
from protocol import MAX_LINE_BYTES, ProtocolError, answer, dumps, hello, loads, query
from scoring import aggregate, score_case


class Session:
    def __init__(self, command, cwd, environment, seconds, line_seconds):
        self.started = time.monotonic()
        self.deadline = self.started + seconds
        self.line_seconds = line_seconds
        self.process = subprocess.Popen(
            command, cwd=cwd, env=environment, stdin=subprocess.PIPE,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, bufsize=0,
            start_new_session=True, close_fds=True,
        )
        self.selector = selectors.DefaultSelector()
        self.selector.register(self.process.stdout, selectors.EVENT_READ, "stdout")
        self.selector.register(self.process.stderr, selectors.EVENT_READ, "stderr")
        self.buffer = bytearray()
        self.stdout_bytes = 0
        self.stderr_bytes = 0
        self.stdout_eof = False

    def send(self, message):
        try:
            self.process.stdin.write((dumps(message) + "\n").encode())
            self.process.stdin.flush()
        except (BrokenPipeError, OSError) as error:
            raise ProtocolError("policy closed stdin") from error

    def pump(self, deadline):
        remaining = min(deadline, self.deadline) - time.monotonic()
        if remaining <= 0:
            raise ProtocolError("runtime or response timeout")
        events = self.selector.select(min(remaining, 0.1))
        for key, mask in events:
            chunk = os.read(key.fileobj.fileno(), 8192)
            if not chunk:
                self.selector.unregister(key.fileobj)
                if key.data == "stdout":
                    self.stdout_eof = True
                continue
            if key.data == "stderr":
                self.stderr_bytes += len(chunk)
                if self.stderr_bytes > 65536:
                    raise ProtocolError("stderr limit exceeded")
            else:
                self.stdout_bytes += len(chunk)
                self.buffer.extend(chunk)
                if self.stdout_bytes > 1048576:
                    raise ProtocolError("stdout limit exceeded")
                if len(self.buffer.split(b"\n", 1)[0]) > MAX_LINE_BYTES:
                    raise ProtocolError("JSONL line too long")

    def receive(self):
        deadline = time.monotonic() + self.line_seconds
        while True:
            if time.monotonic() >= self.deadline:
                raise ProtocolError("runtime timeout")
            if b"\n" in self.buffer:
                line, rest = self.buffer.split(b"\n", 1)
                self.buffer = bytearray(rest)
                if len(line) > MAX_LINE_BYTES:
                    raise ProtocolError("JSONL line too long")
                return loads(line)
            if self.stdout_eof:
                raise ProtocolError("EOF before newline-terminated answer")
            self.pump(deadline)

    def finish(self):
        self.process.stdin.close()
        deadline = min(self.deadline, time.monotonic() + 2.0)
        while self.selector.get_map() or self.process.poll() is None:
            if self.buffer:
                raise ProtocolError("extra stdout after answer")
            self.pump(deadline)
        if self.buffer:
            raise ProtocolError("extra stdout after answer")
        if self.process.returncode != 0:
            raise ProtocolError("policy exited nonzero")

    def close(self):
        try:
            os.killpg(self.process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        self.process.wait(timeout=3)
        self.selector.close()
        for stream in (self.process.stdin, self.process.stdout, self.process.stderr):
            stream.close()


def run_case(record, submission, entry, participant, scratch_root, seconds=45,
             line_seconds=15, sandbox_wrapper=None, command_override=None):
    instance = record["instance"]
    result = {"id": record["id"], "family": instance.family, "status": "invalid", "calls": 0}
    oracle = Oracle(instance, record["noise_seed"])
    session = None
    started = time.monotonic()
    with tempfile.TemporaryDirectory(prefix="case-", dir=scratch_root) as scratch:
        environment = {
            "PATH": str(Path(sys.executable).parent) + os.pathsep + os.defpath,
            "HOME": scratch, "TMPDIR": scratch, "LANG": "C.UTF-8",
            "PYTHONDONTWRITEBYTECODE": "1", "PYTHONHASHSEED": "0",
            "OPENBLAS_NUM_THREADS": "1", "OMP_NUM_THREADS": "1", "MKL_NUM_THREADS": "1",
            "RADIAL_INPUT": str(participant / "input"),
        }
        if command_override is not None:
            command = command_override
        elif sandbox_wrapper:
            command = [
                sys.executable, str(sandbox_wrapper), "--submission", str(submission),
                "--participant", str(participant), "--scratch", scratch,
                "--entry", entry, "--seconds", str(math.ceil(seconds)),
            ]
        else:
            command = [sys.executable, "-u", str(submission / entry)]
        try:
            session = Session(command, submission, environment, seconds, line_seconds)
            session.send(hello())
            while True:
                message = session.receive()
                if message.get("type") == "answer":
                    estimate, radii = answer(message)
                    session.finish()
                    result.update(score_case(instance, estimate, radii))
                    result["status"] = "ok"
                    break
                time_value, probe = query(message)
                if oracle.used >= BUDGET:
                    raise ProtocolError("measurement budget exceeded")
                session.send(oracle.measure(time_value, probe))
        except (ProtocolError, OSError, subprocess.SubprocessError) as error:
            result["reason"] = str(error)
        finally:
            if session:
                session.close()
            result["calls"] = oracle.used
            result["elapsed_seconds"] = round(time.monotonic() - started, 4)
            result["runtime_seconds"] = result["elapsed_seconds"]
            result["runtime_score"] = (
                100 * max(0.0, 1 - result["runtime_seconds"] / 45)
                if result["status"] == "ok" else 0.0
            )
            result.setdefault("reason", "Valid protocol and final answer.")
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--submission", required=True, type=Path)
    parser.add_argument("--participant", type=Path, default=BASE / "participant")
    parser.add_argument("--entry", default="policy.py")
    parser.add_argument("--report", "--output", dest="report", required=True, type=Path)
    parser.add_argument("--split", default="tournament-v1")
    parser.add_argument("--per-family", type=int, default=8)
    parser.add_argument("--seed-file", type=Path)
    parser.add_argument("--sandbox-wrapper", type=Path)
    parser.add_argument("--allow-unsandboxed", action="store_true")
    parser.add_argument("--seconds", type=float, default=45)
    parser.add_argument("--response-seconds", type=float, default=15)
    parser.add_argument("--scratch", type=Path, default=BASE / "evaluator" / ".scratch")
    args = parser.parse_args()
    if args.per_family < 1 or args.per_family > 100:
        parser.error("per-family must be in [1,100]")
    if not math.isfinite(args.seconds) or args.seconds <= 0:
        parser.error("seconds must be positive and finite")
    if not math.isfinite(args.response_seconds) or args.response_seconds <= 0:
        parser.error("response-seconds must be positive and finite")
    submission, participant = args.submission.resolve(), args.participant.resolve()
    if Path(args.entry).is_absolute() or ".." in Path(args.entry).parts:
        parser.error("entry must stay inside the submission directory")
    if not (submission / args.entry).is_file():
        parser.error("submission entry does not exist")
    sandbox_wrapper = args.sandbox_wrapper
    candidate = BASE.parent / "authoring" / "sandbox.py"
    if sandbox_wrapper is None and candidate.is_file():
        sandbox_wrapper = candidate
    if sandbox_wrapper is not None:
        sandbox_wrapper = sandbox_wrapper.resolve()
        if not sandbox_wrapper.is_file():
            parser.error("sandbox wrapper does not exist")
    if not sandbox_wrapper and not args.allow_unsandboxed:
        parser.error("supply --sandbox-wrapper, or --allow-unsandboxed for TRUSTED diagnostics only")
    args.scratch.mkdir(parents=True, exist_ok=True)
    target_bytes = (INPUT / "target.json").read_bytes()
    target = json.loads(target_bytes)
    official = bool(
        sandbox_wrapper and target["frozen"]
        and args.per_family >= target["minimum_cases_per_family"]
        and args.split.startswith("tournament-")
        and args.seconds == 45 and args.response_seconds == 15
    )
    records = suite(args.split, args.per_family, args.seed_file)
    cases = []
    for index, record in enumerate(records):
        cases.append(run_case(
            record, submission, args.entry, participant, args.scratch.resolve(),
            args.seconds, args.response_seconds, sandbox_wrapper,
        ))
        print(f"case {index + 1}/{len(records)}: {cases[-1]['status']}", file=sys.stderr, flush=True)
    report = {
        "version": VERSION, "split": args.split, "per_family": args.per_family,
        "isolation": "external-wrapper" if sandbox_wrapper else "TRUSTED-ONLY-unsandboxed",
        "target_sha256": hashlib.sha256(target_bytes).hexdigest(),
        "target": target, "cases": cases, **aggregate(cases, target, official),
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, allow_nan=False, indent=2) + "\n")
    print(json.dumps({key: value for key, value in report.items() if key not in ("cases", "families")}))


if __name__ == "__main__":
    main()
