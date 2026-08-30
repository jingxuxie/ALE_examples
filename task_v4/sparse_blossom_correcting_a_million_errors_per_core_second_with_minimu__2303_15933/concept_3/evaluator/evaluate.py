import argparse
import hashlib
import hmac
import json
import os
from pathlib import Path
import secrets
import selectors
import signal
import subprocess
import time

import numpy as np

from hidden.simulator import sample_events


ROOT = Path(__file__).resolve().parents[1]
TARGETS = json.loads((ROOT / "evaluator/hidden/targets.json").read_text())


class InvalidEpisode(Exception):
    pass


def worker_command(submission, worker):
    submission = Path(submission).resolve(strict=True)
    if not submission.is_dir() or not submission.is_relative_to(ROOT):
        raise ValueError("Submission must be a directory inside concept_3")
    relative = submission.relative_to(ROOT)
    if len(relative.parts) < 2 or relative.parts[0] not in ("attempts", "champions", "adversary"):
        raise ValueError("Mount a submission leaf, e.g. attempts/v_1, never a private parent")
    command = ["/usr/bin/bwrap", "--unshare-all", "--die-with-parent", "--new-session", "--cap-drop", "ALL"]
    for directory in ("/usr", "/lib", "/lib64", "/bin", "/etc"):
        if Path(directory).exists():
            command.extend(["--ro-bind", directory, directory])
    command.extend(["--proc", "/proc", "--dev", "/dev", "--tmpfs", "/tmp",
                    "--ro-bind", str(ROOT / "participant"), "/participant",
                    "--bind", str(submission), "/submission",
                    "--ro-bind", str(ROOT / "evaluator/hidden/worker_supervisor.py"), "/supervisor.py",
                    "--chdir", "/submission", "--clearenv"])
    environment = {"PATH": "/usr/bin:/bin", "HOME": "/tmp", "TMPDIR": "/tmp",
                   "OPENBLAS_NUM_THREADS": "1", "OMP_NUM_THREADS": "1", "MKL_NUM_THREADS": "1",
                   "NUMEXPR_NUM_THREADS": "1", "PYTHONDONTWRITEBYTECODE": "1", "PYTHONUNBUFFERED": "1"}
    for name, value in environment.items():
        command.extend(["--setenv", name, value])
    command.extend(["/usr/bin/python3", "-I", "/supervisor.py"] + worker)
    return command


class Lines:
    def __init__(self, process):
        self.process = process
        self.buffer = bytearray()
        self.selector = selectors.DefaultSelector()
        self.selector.register(process.stdout, selectors.EVENT_READ)

    def read(self, deadline):
        while b"\n" not in self.buffer:
            remaining = deadline - time.monotonic()
            if remaining <= 0 or not self.selector.select(remaining):
                raise InvalidEpisode("wall_watchdog")
            chunk = os.read(self.process.stdout.fileno(), 65536)
            if not chunk:
                raise InvalidEpisode("worker_closed_pipe")
            self.buffer.extend(chunk)
            if len(self.buffer) > 1048576:
                raise InvalidEpisode("output_line_too_large")
        line, _, tail = self.buffer.partition(b"\n")
        self.buffer = bytearray(tail)
        try:
            message = json.loads(line)
        except (ValueError, UnicodeDecodeError):
            raise InvalidEpisode("invalid_json")
        if not isinstance(message, dict):
            raise InvalidEpisode("message_must_be_object")
        return message

    def close(self):
        self.selector.close()


def send(process, message, deadline):
    payload = memoryview((json.dumps(message, allow_nan=False, separators=(",", ":")) + "\n").encode())
    with selectors.DefaultSelector() as writable:
        writable.register(process.stdin, selectors.EVENT_WRITE)
        while payload:
            remaining = deadline - time.monotonic()
            if remaining <= 0 or not writable.select(remaining):
                raise InvalidEpisode("wall_watchdog")
            try:
                written = os.write(process.stdin.fileno(), payload)
            except BlockingIOError:
                continue
            payload = payload[written:]


def run_episode(episode, submission, worker, transcript=None, cpu_limit=None):
    spec = episode["spec"]
    rates = np.array(episode["rates"])
    rng = np.random.default_rng(episode["sample_seed"])
    secret = secrets.token_bytes(32)
    cpu_limit = TARGETS["cpu_seconds_per_episode"] if cpu_limit is None else cpu_limit
    command = worker_command(submission, worker)
    start = time.monotonic()
    process = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                               stderr=subprocess.DEVNULL, close_fds=True, start_new_session=True,
                               env={"PATH": "/usr/bin:/bin"})
    os.set_blocking(process.stdin.fileno(), False)
    lines = Lines(process)
    shots_used = 0
    queries = 0
    history = []
    final_rates = None
    meter = None
    reason = "ok"
    try:
        send(process, {"key": secret.hex(), "cpu_limit": cpu_limit}, start + TARGETS["initialization_allowance_seconds"])
        ready = lines.read(start + TARGETS["initialization_allowance_seconds"])
        expected = hmac.new(secret, b"ready", hashlib.sha256).hexdigest()
        if ready.get("type") != "_ready" or not hmac.compare_digest(str(ready.get("auth", "")), expected):
            raise InvalidEpisode("supervisor_initialization_failed")
        deadline = time.monotonic() + TARGETS["wall_seconds_per_episode"]
        send(process, {"type": "hello", "spec": spec}, deadline)
        while True:
            message = lines.read(deadline)
            kind = message.get("type")
            if kind == "_meter":
                encoded = json.dumps(message.get("meter"), sort_keys=True, separators=(",", ":"))
                expected = hmac.new(secret, encoded.encode(), hashlib.sha256).hexdigest()
                if not hmac.compare_digest(str(message.get("auth", "")), expected):
                    raise InvalidEpisode("invalid_cpu_authentication")
                meter = message["meter"]
                if meter["cpu_seconds"] > cpu_limit + 0.05:
                    raise InvalidEpisode("cpu_limit")
                if meter["exit_status"] != 0:
                    raise InvalidEpisode("worker_nonzero_exit")
                if final_rates is None:
                    raise InvalidEpisode("missing_final")
                break
            if final_rates is not None:
                raise InvalidEpisode("output_after_final")
            if kind == "query":
                if set(message) != {"type", "action", "shots"}:
                    raise InvalidEpisode("query_keys")
                action = message["action"]
                shots = message["shots"]
                if type(action) is not int or not 0 <= action < len(spec["actions"]):
                    raise InvalidEpisode("invalid_action")
                if type(shots) is not int or not 1 <= shots <= spec["max_shots_per_query"]:
                    raise InvalidEpisode("invalid_shots")
                if queries >= spec["max_queries"] or shots_used + shots > spec["shot_budget"]:
                    raise InvalidEpisode("query_budget")
                counts = sample_events(spec, rates, action, shots, rng)
                shots_used += shots
                queries += 1
                response = {"type": "observation", "action": action, "shots": shots,
                            "counts": counts.tolist(), "shots_remaining": spec["shot_budget"] - shots_used,
                            "queries_remaining": spec["max_queries"] - queries}
                history.append({"query": message, "observation": response})
                send(process, response, deadline)
            elif kind == "final":
                if set(message) != {"type", "rates"} or not isinstance(message["rates"], list):
                    raise InvalidEpisode("final_keys")
                if any(type(value) not in (int, float) for value in message["rates"]):
                    raise InvalidEpisode("invalid_rates")
                final_rates = np.array(message["rates"], dtype=float)
                if final_rates.shape != rates.shape or not np.all(np.isfinite(final_rates)) or np.any(final_rates <= 0):
                    raise InvalidEpisode("invalid_rates")
                process.stdin.close()
            else:
                raise InvalidEpisode("unknown_message")
        process.wait(timeout=max(1.0, deadline - time.monotonic()))
        if process.returncode != 0:
            raise InvalidEpisode("sandbox_nonzero_exit")
    except (InvalidEpisode, BrokenPipeError, OSError, ValueError, subprocess.TimeoutExpired) as error:
        reason = str(error) if isinstance(error, InvalidEpisode) else type(error).__name__
    finally:
        if process.poll() is None:
            os.killpg(process.pid, signal.SIGKILL)
            process.wait()
        lines.close()
        process.stdout.close()
        if not process.stdin.closed:
            process.stdin.close()
    valid = reason == "ok"
    family_mse = {}
    if valid:
        errors = (np.log(final_rates) - np.log(rates)) ** 2
        for family in sorted({channel["family"] for channel in spec["channels"]}):
            indices = [index for index, channel in enumerate(spec["channels"]) if channel["family"] == family]
            family_mse[family] = float(np.mean(errors[indices]))
    if transcript is not None:
        Path(transcript).write_text(json.dumps({"spec": spec, "history": history,
                                              "estimated_rates": None if final_rates is None else final_rates.tolist()}, indent=2))
    return {"id": episode["id"], "regime": spec["regime"], "valid": valid, "reason": reason,
            "family_mse": family_mse, "shots_used": shots_used, "queries": queries,
            "cpu_seconds": None if meter is None else meter["cpu_seconds"],
            "wall_seconds": time.monotonic() - start}


def aggregate(results):
    valid = bool(results) and all(result["valid"] for result in results)
    cells = {}
    if valid:
        for result in results:
            for family, value in result["family_mse"].items():
                cells.setdefault(result["regime"] + "/" + family, []).append(value)
    cell_rmse = {name: float(np.sqrt(np.mean(values))) for name, values in cells.items()}
    mean_error = float(np.mean(list(cell_rmse.values()))) if valid else None
    worst_error = max(cell_rmse.values()) if valid else None
    passed = valid and mean_error <= TARGETS["mean_family_log_rmse_max"] and worst_error <= TARGETS["worst_regime_family_log_rmse_max"]
    cpu = max((result["cpu_seconds"] or 0.0 for result in results), default=0.0)
    return {"valid": valid, "passed": bool(passed), "reason": "ok" if passed else ("accuracy_threshold" if valid else "invalid_episode"),
            "core_score": None if not valid else float(np.exp(-mean_error)),
            "worst_family_score": None if not valid else float(np.exp(-worst_error)),
            "runtime_score": max(0.0, 1.0 - cpu / TARGETS["cpu_seconds_per_episode"]),
            "mean_family_log_rmse": mean_error, "worst_regime_family_log_rmse": worst_error,
            "family_log_rmse": cell_rmse, "episodes": results, "targets": TARGETS}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--suite", choices=("private", "training"), default="private")
    parser.add_argument("--submission", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--limit", type=int)
    parser.add_argument("--transcript-dir")
    parser.add_argument("worker", nargs=argparse.REMAINDER)
    arguments = parser.parse_args()
    manifest = json.loads((ROOT / "evaluator/hidden/freeze.json").read_text())
    for relative, key in (("evaluator/hidden/targets.json", "targets_sha256"),
                          ("evaluator/hidden/episodes.json", "episodes_sha256")):
        if hashlib.sha256((ROOT / relative).read_bytes()).hexdigest() != manifest[key]:
            raise RuntimeError("Frozen package integrity check failed")
    source = ROOT / ("evaluator/hidden/episodes.json" if arguments.suite == "private" else "participant/input/training.json")
    episodes = json.loads(source.read_text())["episodes"]
    if arguments.limit:
        episodes = episodes[:arguments.limit]
    worker = arguments.worker
    if worker and worker[0] == "--":
        worker = worker[1:]
    if not worker:
        parser.error("Specify worker command after --")
    results = []
    for episode in episodes:
        transcript = None
        if arguments.transcript_dir:
            directory = Path(arguments.transcript_dir)
            directory.mkdir(parents=True, exist_ok=True)
            transcript = directory / (episode["id"] + ".json")
        result = run_episode(episode, arguments.submission, worker, transcript)
        results.append(result)
        print(json.dumps(result), flush=True)
    report = aggregate(results)
    report["official_suite"] = arguments.suite == "private" and len(episodes) == 12
    report["targets_sha256"] = hashlib.sha256((ROOT / "evaluator/hidden/targets.json").read_bytes()).hexdigest()
    Path(arguments.output).write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")


if __name__ == "__main__":
    main()
