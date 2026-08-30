import json
import os
import resource
import selectors
import signal
import subprocess
import time
from pathlib import Path

import numpy as np

from model import CONFIG, normalized_error, probabilities, validate_estimate, validate_experiment


class ProtocolError(Exception):
    pass


class StartupError(ProtocolError):
    pass


def strict_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON key")
        result[key] = value
    return result


def reject_constant(value):
    raise ValueError("nonfinite JSON constant")


def child_limits():
    limits = CONFIG["resources"]
    resource.setrlimit(resource.RLIMIT_CPU, (limits["cpu_seconds"], limits["cpu_seconds"] + 1))
    memory = limits["memory_mb"] * 1024**2
    resource.setrlimit(resource.RLIMIT_AS, (memory, memory))
    resource.setrlimit(resource.RLIMIT_FSIZE, (8 * 1024**2, 8 * 1024**2))
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    resource.setrlimit(resource.RLIMIT_NOFILE, (64, 64))
    if hasattr(os, "sched_setaffinity"):
        available_cpus = sorted(os.sched_getaffinity(0))
        os.sched_setaffinity(0, {available_cpus[os.getpid() % len(available_cpus)]})
    os.umask(0o077)


class JsonProcess:
    def __init__(self, command, wall_seconds=None, cwd=None, startup_handshake=False):
        self.started = time.monotonic()
        self.solver_started = None if startup_handshake else self.started
        self.wall_limit = wall_seconds or CONFIG["resources"]["wall_seconds"]
        self.deadline = self.started + (90 if startup_handshake else self.wall_limit)
        environment = {"PATH": "/usr/bin:/bin", "HOME": "/tmp", "TMPDIR": "/tmp", "PYTHONDONTWRITEBYTECODE": "1"}
        environment["PYTHONPATH"] = str(Path(__file__).resolve().parent)
        environment.update({name: "1" for name in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS")})
        self.process = subprocess.Popen(command, cwd=cwd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                        start_new_session=True, preexec_fn=child_limits, env=environment, bufsize=0)
        self.selector = selectors.DefaultSelector()
        for name in ("stdin", "stdout", "stderr"):
            stream = getattr(self.process, name)
            os.set_blocking(stream.fileno(), False)
            if name != "stdin":
                self.selector.register(stream, selectors.EVENT_READ, name)
        self.output = bytearray()
        self.stderr = bytearray()
        self.stdout_bytes = 0
        self.stdout_closed = False

    def await_startup(self):
        try:
            marker = self.receive()
            if marker != {"sandbox_ready": True}:
                raise ProtocolError("missing trusted sandbox startup marker")
        except ProtocolError as error:
            raise StartupError("sandbox startup failed: " + str(error)) from error
        self.solver_started = time.monotonic()
        self.deadline = self.solver_started + self.wall_limit
        self.stdout_bytes -= len(b'{"sandbox_ready":true}\n')

    def pump(self):
        remaining = self.deadline - time.monotonic()
        if remaining <= 0:
            raise ProtocolError("wall time exceeded")
        for key, events in self.selector.select(min(remaining, 0.1)):
            if key.data == "stdin":
                continue
            chunk = os.read(key.fileobj.fileno(), 65536)
            if not chunk:
                self.selector.unregister(key.fileobj)
                if key.data == "stdout":
                    self.stdout_closed = True
                continue
            if key.data == "stdout":
                self.stdout_bytes += len(chunk)
                if self.stdout_bytes > CONFIG["resources"]["stdout_bytes"]:
                    raise ProtocolError("stdout limit exceeded")
                self.output.extend(chunk)
                first_newline = self.output.find(b"\n")
                if first_newline > CONFIG["resources"]["line_bytes"] or (first_newline < 0 and len(self.output) > CONFIG["resources"]["line_bytes"]):
                    raise ProtocolError("line limit exceeded")
            else:
                self.stderr.extend(chunk)
                if len(self.stderr) > CONFIG["resources"]["stderr_bytes"]:
                    raise ProtocolError("stderr limit exceeded")

    def send(self, message):
        pending = memoryview((json.dumps(message, allow_nan=False, separators=(",", ":")) + "\n").encode())
        while pending:
            if time.monotonic() >= self.deadline:
                raise ProtocolError("wall time exceeded")
            try:
                written = os.write(self.process.stdin.fileno(), pending)
                pending = pending[written:]
            except BlockingIOError:
                self.selector.register(self.process.stdin, selectors.EVENT_WRITE, "stdin")
                try:
                    self.pump()
                finally:
                    self.selector.unregister(self.process.stdin)
            except BrokenPipeError as error:
                raise ProtocolError("controller closed stdin") from error

    def receive(self):
        while b"\n" not in self.output:
            if self.stdout_closed:
                raise ProtocolError("EOF before a complete message")
            self.pump()
        line, remainder = self.output.split(b"\n", 1)
        self.output = bytearray(remainder)
        if len(line) > CONFIG["resources"]["line_bytes"]:
            raise ProtocolError("line limit exceeded")
        try:
            message = json.loads(line.decode("utf-8"), object_pairs_hook=strict_object, parse_constant=reject_constant)
        except (ValueError, UnicodeError, RecursionError) as error:
            raise ProtocolError("invalid JSON: " + str(error)) from error
        if not isinstance(message, dict):
            raise ProtocolError("message must be an object")
        return message

    def finish(self):
        self.process.stdin.close()
        while not self.stdout_closed or self.process.poll() is None or self.selector.get_map():
            self.pump()
        if self.output.strip():
            raise ProtocolError("stdout after final estimate")
        if self.process.returncode != 0:
            raise ProtocolError("nonzero controller exit: " + str(self.process.returncode))

    def close(self):
        try:
            os.killpg(self.process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        self.process.wait()
        self.selector.close()
        for name in ("stdin", "stdout", "stderr"):
            getattr(self.process, name).close()


def start_message():
    return {"type": "start", **{key: CONFIG[key] for key in ("protocol", "budget", "parameter_order", "bounds", "normalization")}}


def run_episode(command, parameters, measurement_seed, wall_seconds=None, cwd=None, startup_handshake=False):
    rng = np.random.default_rng(measurement_seed)
    shots_used = 0
    queries_used = 0
    session = None
    started = time.monotonic()
    cpu_before = resource.getrusage(resource.RUSAGE_CHILDREN)
    result = {"valid": False, "nrmse": 30.0, "reason": "controller did not start"}
    try:
        session = JsonProcess(command, wall_seconds=wall_seconds, cwd=cwd, startup_handshake=startup_handshake)
        if startup_handshake:
            session.await_startup()
        session.send(start_message())
        while True:
            message = session.receive()
            if message.get("type") == "estimate":
                omega = validate_estimate(message)
                session.finish()
                result = {"valid": True, "nrmse": normalized_error(omega, parameters), "omega": omega.tolist(), "reason": "ok"}
                break
            experiment = validate_experiment(message)
            if queries_used >= CONFIG["budget"]["queries"] or shots_used + experiment["shots"] > CONFIG["budget"]["shots"]:
                raise ProtocolError("experiment budget exceeded")
            chance = float(probabilities(parameters, [experiment])[0])
            plus = int(rng.binomial(experiment["shots"], chance))
            shots_used += experiment["shots"]
            session.send({"type": "result", "query": queries_used, "plus": plus, "shots": experiment["shots"],
                          "remaining_shots": CONFIG["budget"]["shots"] - shots_used,
                          "remaining_queries": CONFIG["budget"]["queries"] - queries_used - 1})
            queries_used += 1
    except StartupError as error:
        result["reason"] = str(error)
        result["infrastructure_error"] = True
    except (ProtocolError, ValueError, OSError, OverflowError) as error:
        result["reason"] = str(error)
        if startup_handshake and (session is None or session.solver_started is None):
            result["infrastructure_error"] = True
    finally:
        if session is not None:
            session.close()
            result["stderr_tail"] = bytes(session.stderr[-4096:]).decode("utf-8", errors="replace")
            result["stdout_bytes"] = session.stdout_bytes
    cpu_after = resource.getrusage(resource.RUSAGE_CHILDREN)
    finished = time.monotonic()
    solver_started = session.solver_started if session is not None else None
    result.update({"wall_seconds": finished - solver_started if solver_started is not None else 0.0,
                   "startup_wall_seconds": solver_started - started if solver_started is not None else finished - started,
                   "total_wall_seconds": finished - started,
                   "cpu_seconds": cpu_after.ru_utime + cpu_after.ru_stime - cpu_before.ru_utime - cpu_before.ru_stime,
                   "shots": shots_used, "queries": queries_used})
    return result


def aggregate(results):
    families = sorted({result["family"] for result in results})
    family_scores = {family: float(np.mean([result["nrmse"] for result in results if result["family"] == family])) for family in families}
    mean_error = float(np.mean([result["nrmse"] for result in results]))
    worst_error = max(family_scores.values())
    valid = all(result["valid"] for result in results)
    valid_fraction = sum(result["valid"] for result in results) / len(results)
    passed = valid and mean_error <= CONFIG["target"]["mean_nrmse"] and worst_error <= CONFIG["target"]["worst_family_mean_nrmse"]
    return {"core_score": mean_error, "mean_nrmse": mean_error, "worst_family_score": worst_error,
            "family_mean_nrmse": family_scores, "valid": valid, "passed": passed,
            "valid_fraction": valid_fraction, "resource_score": valid_fraction,
            "reason": "target met" if passed else ("invalid episodes" if not valid else "recovery target not met"),
            "runtime": {"total_wall_seconds": sum(result["total_wall_seconds"] for result in results),
                        "total_solver_wall_seconds": sum(result["wall_seconds"] for result in results),
                        "total_startup_wall_seconds": sum(result["startup_wall_seconds"] for result in results),
                        "maximum_episode_wall_seconds": max(result["wall_seconds"] for result in results),
                        "total_cpu_seconds": sum(result["cpu_seconds"] for result in results)},
            "episode_count": len(results), "target": CONFIG["target"]}
