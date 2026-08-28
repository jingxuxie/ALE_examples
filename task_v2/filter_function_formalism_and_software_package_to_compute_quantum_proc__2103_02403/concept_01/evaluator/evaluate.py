#!/usr/bin/env python3
"""Private full-channel evaluator and artifact-based release-evidence audit."""

import argparse
import ast
import csv
import io
import json
import math
import os
from pathlib import Path
import re
import resource
import selectors
import shutil
import signal
import struct
import subprocess
import sys
import tempfile
import time
import traceback
import uuid
import zipfile
import zlib
from dataclasses import dataclass


THREAD_ENV = {
    name: "1" for name in (
        "OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS",
        "NUMEXPR_NUM_THREADS", "VECLIB_MAXIMUM_THREADS", "BLIS_NUM_THREADS",
    )
}
os.environ.update(THREAD_ENV)

import numpy as np
from scipy.linalg import expm


HERE = Path(__file__).resolve().parent
TIME_LIMIT = 120.0
MEMORY_LIMIT = 2 * 1024 ** 3
FILE_LIMIT = 64 * 1024 ** 2
TEXT_LIMIT = 8 * 1024 ** 2
LOG_LIMIT = 128 * 1024
TABLE_LIMIT = 2000
RTOL = 1e-6
ATOL = 1e-8
RERUN_RTOL = 1e-5
PHYSICALITY_LIMIT = 1e-4
SCALARS = ("infidelity", "leakage", "coherent_size", "k2_norm")
RESOURCES = ("seconds", "peak_rss_mb")
OBSERVABLES = SCALARS + ("tp_error", "unital_error", "choi_min")
ROW_FIELDS = ("row_id", "case_id", "mode") + SCALARS + RESOURCES + ("artifact",)
TABLES = ("results.csv", "ablation.csv", "scaling.csv")
MODES = ("selected", "baseline", "refined", "no_memory")
GROUPS = ("tables", "coverage", "ablations", "scaling", "claims", "reruns", "figures", "report")


class InfrastructureError(RuntimeError):
    def __init__(self, message, details=None):
        super().__init__(message)
        self.details = details


class InvalidArtifact(ValueError):
    pass


def contained_path(root, relative, directory=False):
    if not isinstance(relative, str) or not relative or "\x00" in relative:
        raise InvalidArtifact("Expected a nonempty relative path")
    requested = Path(relative)
    if requested.is_absolute() or ".." in requested.parts:
        raise InvalidArtifact(f"Path escape rejected: {relative!r}")
    resolved_root = Path(root).resolve()
    try:
        resolved = (resolved_root / requested).resolve(strict=True)
    except (OSError, RuntimeError) as error:
        raise InvalidArtifact(f"Unavailable path {relative!r}: {error}") from error
    if not resolved.is_relative_to(resolved_root):
        raise InvalidArtifact(f"Symlink escape rejected: {relative!r}")
    if not (resolved.is_dir() if directory else resolved.is_file()):
        raise InvalidArtifact(f"Not a {'directory' if directory else 'regular file'}: {relative!r}")
    return resolved


def read_bytes(path, limit=TEXT_LIMIT):
    with Path(path).open("rb") as stream:
        contents = stream.read(limit + 1)
    if len(contents) > limit:
        raise InvalidArtifact(f"File exceeds {limit} bytes: {path}")
    return contents


def reject_constant(value):
    raise InvalidArtifact(f"Nonfinite JSON constant: {value}")


def bounded_integer(value):
    if len(value) > 128:
        raise InvalidArtifact("Oversized JSON integer")
    return int(value)


def read_json(path):
    document = json.loads(read_bytes(path).decode("utf-8"), parse_constant=reject_constant,
                          parse_float=finite_float, parse_int=bounded_integer)
    pending = [(document, 0)]
    count = 0
    while pending:
        value, depth = pending.pop()
        count += 1
        if depth > 64 or count > 100000:
            raise InvalidArtifact("JSON nesting or element limit exceeded")
        if isinstance(value, dict):
            pending.extend((item, depth + 1) for item in value.values())
        elif isinstance(value, list):
            pending.extend((item, depth + 1) for item in value)
    return document


def finite_float(value):
    if isinstance(value, (bool, np.bool_)):
        raise InvalidArtifact("Boolean is not a numeric measurement")
    try:
        number = float(value)
    except (ValueError, TypeError, OverflowError) as error:
        raise InvalidArtifact(f"Invalid numeric measurement: {value!r}") from error
    if not math.isfinite(number):
        raise InvalidArtifact(f"Nonfinite numeric measurement: {value!r}")
    return number


def agrees(actual, claimed):
    return bool(np.isclose(actual, finite_float(claimed), rtol=RTOL, atol=ATOL))


def load_archive(path, required, expected_shape=None):
    contents = read_bytes(path, FILE_LIMIT)
    arrays = {}
    with zipfile.ZipFile(io.BytesIO(contents)) as archive:
        members = archive.infolist()
        names = [member.filename for member in members]
        if len(members) > 64 or len(set(names)) != len(names):
            raise InvalidArtifact("NPZ has too many or duplicate members")
        if sum(member.file_size for member in members) > FILE_LIMIT:
            raise InvalidArtifact("Uncompressed NPZ exceeds the artifact size limit")
        for key in required:
            name = key + ".npy"
            if name not in names:
                raise InvalidArtifact(f"Missing NPZ array: {key}")
            payload = archive.read(name)
            stream = io.BytesIO(payload)
            if stream.read(6) != b"\x93NUMPY":
                raise InvalidArtifact(f"Invalid NPY signature: {key}")
            version = tuple(stream.read(2))
            if version not in ((1, 0), (2, 0), (3, 0)):
                raise InvalidArtifact(f"Unsupported NPY version: {version}")
            length_size = 2 if version == (1, 0) else 4
            header_size = int.from_bytes(stream.read(length_size), "little")
            if header_size > 16384:
                raise InvalidArtifact("Oversized NPY header")
            header = ast.literal_eval(stream.read(header_size).decode("utf-8" if version == (3, 0) else "latin1"))
            shape = header["shape"]
            dtype = np.dtype(header["descr"])
            if not isinstance(shape, tuple) or any(type(size) is not int or size < 0 for size in shape):
                raise InvalidArtifact(f"Invalid array shape: {key}")
            if dtype.hasobject or dtype.kind not in "biufc":
                raise InvalidArtifact(f"Non-numeric array: {key}")
            if expected_shape is not None and shape != expected_shape:
                raise InvalidArtifact(f"Invalid {key} shape {shape}; expected {expected_shape}")
            data_size = math.prod(shape) * dtype.itemsize
            if data_size > FILE_LIMIT or data_size != len(payload) - stream.tell():
                raise InvalidArtifact(f"Invalid or oversized array payload: {key}")
            arrays[key] = np.load(io.BytesIO(payload), allow_pickle=False)
            if not np.isfinite(arrays[key]).all():
                raise InvalidArtifact(f"Nonfinite values in {key}")
    return arrays


@dataclass
class Case:
    case_id: str
    family: str
    path: Path
    asset: Path
    description: dict
    arrays: dict
    ideal: np.ndarray

    @property
    def dimension(self):
        return self.arrays["H"].shape[-1]

    @property
    def segments(self):
        return len(self.arrays["dt"])


def load_cases(root):
    try:
        manifest = read_json(root / "manifest.json")
        if not isinstance(manifest, list) or not manifest:
            raise InvalidArtifact("Manifest must be a nonempty list")
        cases = {}
        for entry in manifest:
            case_id = entry["case_id"]
            family = entry["family"]
            if not isinstance(case_id, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]*", case_id):
                raise InvalidArtifact("Unsafe case_id in manifest")
            if case_id in cases or not isinstance(family, str) or not family:
                raise InvalidArtifact(f"Duplicate case or invalid family: {case_id}")
            path = contained_path(root / "cases", entry["file"])
            description = read_json(path)
            if description.get("case_id") != case_id:
                raise InvalidArtifact(f"Manifest/JSON case_id mismatch: {case_id}")
            asset = contained_path(path.parent, description["asset"])
            arrays = load_archive(asset, ("dt", "H", "operators", "sensitivity", "blocks", "computational"))
            hamiltonians = arrays["H"]
            durations = arrays["dt"]
            if hamiltonians.ndim != 3 or hamiltonians.shape[1] != hamiltonians.shape[2]:
                raise InvalidArtifact(f"Invalid Hamiltonian shape: {case_id}")
            dimension = hamiltonians.shape[-1]
            if dimension < 1 or durations.shape != (len(hamiltonians),) or not np.all(durations > 0):
                raise InvalidArtifact(f"Invalid segment durations: {case_id}")
            if not np.allclose(hamiltonians, hamiltonians.conj().transpose(0, 2, 1), rtol=0, atol=1e-10):
                raise InvalidArtifact(f"Non-Hermitian input Hamiltonian: {case_id}")
            computational = arrays["computational"]
            if computational.ndim != 1 or not len(computational) or not np.array_equal(computational, computational.astype(int)):
                raise InvalidArtifact(f"Invalid computational subspace: {case_id}")
            if len(np.unique(computational)) != len(computational) or np.any(computational < 0) or np.any(computational >= dimension):
                raise InvalidArtifact(f"Computational indices out of bounds: {case_id}")
            blocks = arrays["blocks"]
            if blocks.ndim != 1 or len(blocks) < 2 or blocks[0] != 0 or blocks[-1] != len(durations) or np.any(np.diff(blocks) <= 0):
                raise InvalidArtifact(f"Invalid block partition: {case_id}")
            if description["noise"]["kind"] not in ("static", "ou", "telegraph", "white", "broadband"):
                raise InvalidArtifact(f"Unknown noise law: {case_id}")
            propagator = np.eye(dimension, dtype=complex)
            for duration, hamiltonian in zip(durations, hamiltonians):
                propagator = expm(-1j * duration * hamiltonian) @ propagator
            ideal = np.kron(propagator.conj(), propagator)
            cases[case_id] = Case(case_id, family, path, asset, description, arrays, ideal)
        return cases
    except Exception as error:
        raise InfrastructureError(f"Invalid evaluator input under {root}: {error}") from error


def observables(case, channel, response):
    dimension = case.dimension
    error_channel = case.ideal.conj().T @ channel
    identity = np.eye(dimension).reshape(-1, order="F")
    computational = case.arrays["computational"].astype(int)
    state = np.zeros((dimension, dimension), dtype=complex)
    state[computational, computational] = 1 / len(computational)
    final_state = (channel @ state.reshape(-1, order="F")).reshape((dimension, dimension), order="F")
    choi = channel.reshape((dimension,) * 4, order="F").transpose(0, 2, 1, 3).reshape((dimension ** 2,) * 2, order="F") / dimension
    measurements = {
        "infidelity": float(1 - np.trace(error_channel).real / dimension ** 2),
        "leakage": float(1 - final_state[computational, computational].real.sum()),
        "coherent_size": float(np.linalg.norm(error_channel - error_channel.conj().T) / 2),
        "k2_norm": float(np.linalg.norm(response)),
        "tp_error": float(np.linalg.norm(identity @ channel - identity)),
        "hermiticity_error": float(np.linalg.norm(choi - choi.conj().T)),
        "unital_error": float(np.linalg.norm(channel @ identity - identity)),
        "choi_min": float(np.linalg.eigvalsh((choi + choi.conj().T) / 2).min()),
    }
    if not all(math.isfinite(value) for value in measurements.values()):
        raise InvalidArtifact("Nonfinite independently recomputed observable")
    return measurements


def load_process(root, case):
    path = contained_path(root, "process.npz")
    arrays = load_archive(path, ("channel", "k2"), (case.dimension ** 2,) * 2)
    measurements = observables(case, arrays["channel"], arrays["k2"])
    if measurements["tp_error"] > PHYSICALITY_LIMIT or measurements["hermiticity_error"] > PHYSICALITY_LIMIT:
        raise InvalidArtifact(f"Channel fails physicality: tp_error={measurements['tp_error']:.9g}, hermiticity_error={measurements['hermiticity_error']:.9g}")
    return arrays, measurements


class LogBuffer:
    def __init__(self):
        self.head = bytearray()
        self.tail = bytearray()
        self.total = 0

    def append(self, data):
        self.total += len(data)
        available = LOG_LIMIT // 2 - len(self.head)
        self.head.extend(data[:available])
        self.tail.extend(data[available:])
        if len(self.tail) > LOG_LIMIT // 2:
            del self.tail[:-LOG_LIMIT // 2]

    def text(self):
        omitted = self.total - len(self.head) - len(self.tail)
        separator = f"\n[... {omitted} log bytes omitted ...]\n".encode() if omitted else b""
        return (bytes(self.head) + separator + bytes(self.tail)).decode("utf-8", errors="replace")


def child_limits():
    resource.setrlimit(resource.RLIMIT_AS, (MEMORY_LIMIT, MEMORY_LIMIT))
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    resource.setrlimit(resource.RLIMIT_FSIZE, (FILE_LIMIT, FILE_LIMIT))
    resource.setrlimit(resource.RLIMIT_CPU, (int(TIME_LIMIT), int(TIME_LIMIT) + 1))


def process_tree(root_pid):
    pending = [root_pid]
    visited = set()
    resident_kb = 0
    while pending:
        process_id = pending.pop()
        if process_id in visited:
            continue
        visited.add(process_id)
        try:
            status = Path(f"/proc/{process_id}/status").read_text()
            match = re.search(r"^VmRSS:\s+(\d+)", status, re.MULTILINE)
            if match:
                resident_kb += int(match.group(1))
            for child_file in Path(f"/proc/{process_id}/task").glob("*/children"):
                pending.extend(int(value) for value in child_file.read_text().split())
        except (OSError, ValueError):
            continue
    return visited, resident_kb


def kill_tree(process_id, descendants):
    try:
        os.killpg(process_id, signal.SIGKILL)
    except ProcessLookupError:
        pass
    for descendant in descendants - {process_id}:
        try:
            os.kill(descendant, signal.SIGKILL)
        except ProcessLookupError:
            pass


def clean_environment(temporary, seed=None):
    environment = {
        "PATH": "/usr/bin:/bin", "HOME": str(temporary), "TMPDIR": str(temporary),
        "LANG": "C.UTF-8", "LC_ALL": "C.UTF-8", "PYTHONPATH": "",
        "PYTHONNOUSERSITE": "1", "PYTHONDONTWRITEBYTECODE": "1", "PYTHONHASHSEED": "0",
        "MPLCONFIGDIR": str(Path(temporary) / "matplotlib"),
        "NUMBA_CACHE_DIR": str(Path(temporary) / "numba"),
        **THREAD_ENV,
    }
    if seed is not None:
        environment.update({"EVALUATOR_SEED": str(seed), "SEED": str(seed), "RANDOM_SEED": str(seed)})
        if 0 <= seed < 2 ** 32:
            environment["PYTHONHASHSEED"] = str(seed)
    return environment


class Runner:
    def __init__(self, output, unsandboxed):
        self.output = output
        self.unsandboxed = unsandboxed
        if not unsandboxed and not os.access("/usr/bin/bwrap", os.X_OK):
            raise InfrastructureError("Required sandbox executable /usr/bin/bwrap is unavailable; no unsandboxed fallback")
        if not hasattr(os, "wait4") or not Path("/proc/self/status").is_file():
            raise InfrastructureError("Linux /proc and wait4 are required for resource accounting")

    def command(self, case_dir, runout, temporary, mode, marker, seed):
        environment = clean_environment(temporary if self.unsandboxed else "/tmp", seed)
        if self.unsandboxed:
            command = ["/bin/bash", str(self.output / "run.sh"), str(case_dir / "input.json"), str(runout), "--mode", mode]
            return command, environment
        command = [
            "/usr/bin/bwrap", "--unshare-all", "--unshare-user", "--unshare-cgroup",
            "--new-session", "--die-with-parent", "--cap-drop", "ALL", "--clearenv",
        ]
        for system_path in ("/usr", "/bin", "/lib", "/lib64"):
            if Path(system_path).exists():
                command.extend(("--ro-bind", system_path, system_path))
        command.extend((
            "--proc", "/proc", "--dev", "/dev", "--tmpfs", "/tmp",
            "--ro-bind", str(self.output), "/candidate", "--ro-bind", str(case_dir), "/case",
            "--bind", str(runout), "/runout", "--chdir", "/runout",
        ))
        command.extend(("--ro-bind", str(self.output), str(self.output)))
        participant = HERE.parent / "participant" / "v_01"
        command.extend(("--ro-bind", str(participant), str(participant)))
        for key, value in environment.items():
            command.extend(("--setenv", key, value))
        command.extend((
            "/bin/sh", "-c", 'printf "%s\\n" "$1"; shift; exec "$@"', "evaluator-launch", marker,
            "/bin/bash", "/candidate/run.sh", "/case/input.json", "/runout", "--mode", mode,
        ))
        return command, environment

    def execute(self, command, environment, runout, marker):
        started = time.monotonic()
        logs = {"stdout": LogBuffer(), "stderr": LogBuffer()}
        sampled_peak = 0
        descendants = set()
        reason = None
        usage = None
        process = None
        try:
            process = subprocess.Popen(
                command, cwd=runout, env=environment, stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=True,
                close_fds=True, preexec_fn=child_limits,
            )
            with selectors.DefaultSelector() as selector:
                for name, stream in (("stdout", process.stdout), ("stderr", process.stderr)):
                    os.set_blocking(stream.fileno(), False)
                    selector.register(stream, selectors.EVENT_READ, name)
                while process.returncode is None:
                    current_descendants, resident_kb = process_tree(process.pid)
                    descendants = current_descendants
                    sampled_peak = max(sampled_peak, resident_kb)
                    if reason is None and time.monotonic() - started > TIME_LIMIT:
                        reason = "timeout"
                        kill_tree(process.pid, descendants)
                    if reason is None and resident_kb * 1024 > MEMORY_LIMIT:
                        reason = "memory_limit"
                        kill_tree(process.pid, descendants)
                    for key, events in selector.select(0.05):
                        data = os.read(key.fileobj.fileno(), 65536)
                        if data:
                            logs[key.data].append(data)
                        else:
                            selector.unregister(key.fileobj)
                    waited_pid, wait_status, waited_usage = os.wait4(process.pid, os.WNOHANG)
                    if waited_pid:
                        usage = waited_usage
                        process.returncode = os.waitstatus_to_exitcode(wait_status)
                kill_tree(process.pid, descendants)
                for key in list(selector.get_map().values()):
                    for attempt in range(32):
                        try:
                            data = os.read(key.fileobj.fileno(), 65536)
                        except BlockingIOError:
                            break
                        if not data:
                            break
                        logs[key.data].append(data)
        except Exception as error:
            raise InfrastructureError(f"Cannot launch or supervise child: {error}") from error
        finally:
            if process is not None:
                if process.returncode is None:
                    kill_tree(process.pid, descendants)
                    process.wait()
                process.stdout.close()
                process.stderr.close()
        elapsed = time.monotonic() - started
        record = {
            "status": reason or ("ok" if process.returncode == 0 else "child_failed"),
            "returncode": process.returncode, "seconds": elapsed,
            "peak_rss_mb": max(sampled_peak, usage.ru_maxrss) / 1024,
            "user_seconds": usage.ru_utime, "system_seconds": usage.ru_stime,
            "sandboxed": not self.unsandboxed, "stdout": logs["stdout"].text(),
            "stderr": logs["stderr"].text(), "errors": [], "warnings": [],
        }
        if not self.unsandboxed:
            prefix = (marker + "\n").encode()
            if not bytes(logs["stdout"].head).startswith(prefix):
                raise InfrastructureError("Bubblewrap failed before candidate execution; sandboxing is not silently disabled", record)
            record["stdout"] = record["stdout"][len(prefix):]
        if record["status"] != "ok":
            record["errors"].append(f"Child {record['status']}; exit={process.returncode}; wall={elapsed:.6f}s; peak_rss={record['peak_rss_mb']:.3f}MiB")
        return record

    def run(self, case, mode="selected", seed=None):
        print(f"[evaluate] {case.case_id} --mode {mode}", file=sys.stderr, flush=True)
        try:
            contained_path(self.output, "run.sh")
        except Exception as error:
            return {"case_id": case.case_id, "mode": mode, "status": "invalid_entrypoint", "seconds": 0.0,
                    "peak_rss_mb": 0.0, "returncode": None, "stdout": "", "stderr": "",
                    "errors": [str(error)], "warnings": [], "sandboxed": not self.unsandboxed}, None
        with tempfile.TemporaryDirectory(prefix="quantum-eval-", dir="/tmp") as temporary_root:
            root = Path(temporary_root)
            case_dir = root / "case"
            runout = root / "runout"
            temporary = root / "tmp"
            for directory in (case_dir, runout, temporary):
                directory.mkdir()
            description = dict(case.description)
            description["asset"] = "data.npz"
            (case_dir / "input.json").write_text(json.dumps(description), encoding="utf-8")
            shutil.copyfile(case.asset, case_dir / "data.npz")
            marker = "EVALUATOR_STARTED_" + uuid.uuid4().hex
            command, environment = self.command(case_dir, runout, temporary, mode, marker, seed)
            record = self.execute(command, environment, runout, marker)
            record.update(case_id=case.case_id, mode=mode, seed_requested=seed)
            arrays = None
            if record["status"] == "ok":
                try:
                    arrays, record["observables"] = load_process(runout, case)
                except Exception as error:
                    record["status"] = "invalid_output"
                    record["errors"].append(f"Invalid process.npz: {error}")
                try:
                    reported = read_json(contained_path(runout, "metrics.json"))
                    if not isinstance(reported, dict):
                        raise InvalidArtifact("metrics.json must be an object")
                    record["reported_metrics"] = reported
                    for name, expected in (("case_id", case.case_id), ("mode", mode)):
                        if reported.get(name) != expected:
                            record["warnings"].append(f"Reported {name} does not match invocation")
                except Exception as error:
                    record["warnings"].append(f"Invalid/missing metrics.json: {error}")
            print(f"[evaluate] {case.case_id}/{mode}: {record['status']} ({record['seconds']:.3f}s, {record['peak_rss_mb']:.1f}MiB)", file=sys.stderr, flush=True)
            return record, arrays


def load_private_targets(cases):
    try:
        budgets = read_json(HERE / "hidden" / "resources.json")
        if not isinstance(budgets, dict):
            raise InvalidArtifact("resources.json must map case_id to reference resources")
        targets = {}
        for case_id, case in cases.items():
            target_path = contained_path(HERE / "hidden" / "targets", case_id + ".npz")
            target = load_archive(target_path, ("channel", "k2"), (case.dimension ** 2,) * 2)
            measurements = observables(case, target["channel"], target["k2"])
            if max(measurements["tp_error"], measurements["hermiticity_error"]) > PHYSICALITY_LIMIT:
                raise InvalidArtifact(f"Invalid target physicality: {case_id}")
            reference = {name: finite_float(budgets[case_id][name]) for name in RESOURCES}
            if reference["seconds"] < 0 or reference["peak_rss_mb"] <= 0:
                raise InvalidArtifact(f"Invalid reference resource budget: {case_id}")
            targets[case_id] = (target, reference)
        return targets
    except Exception as error:
        raise InfrastructureError(f"Missing or invalid private targets/resources: {error}") from error


def relative_error(actual, expected, denominator=None):
    scale = max(float(np.linalg.norm(expected)) if denominator is None else denominator, 1e-8)
    value = float(np.linalg.norm(actual - expected) / scale)
    if not math.isfinite(value):
        raise InvalidArtifact("Nonfinite full-array relative error")
    return value


def accuracy_term(relative, tolerance):
    if relative <= tolerance:
        return 1 / (1 + (relative / tolerance) ** 2)
    inverse = tolerance / relative
    return inverse ** 2 / (1 + inverse ** 2)


def score_case(case, record, arrays, target, reference):
    record.update(family=case.family, accuracy=0.0, channel_rel=None, response_rel=None,
                  efficiency=0.0, time_efficiency=0.0, memory_efficiency=0.0, reference_resources=reference)
    if arrays is None or record["status"] != "ok":
        return
    try:
        channel_scale = float(np.linalg.norm(target["channel"] - case.ideal))
        record["channel_rel"] = relative_error(arrays["channel"], target["channel"], channel_scale)
        record["response_rel"] = relative_error(arrays["k2"], target["k2"])
        record["accuracy"] = 0.6 * accuracy_term(record["channel_rel"], 0.05) + 0.4 * accuracy_term(record["response_rel"], 0.03)
        record["time_efficiency"] = min(1.0, math.sqrt((reference["seconds"] + 0.5) / (record["seconds"] + 0.5)))
        record["memory_efficiency"] = min(1.0, math.sqrt((reference["peak_rss_mb"] + 64) / (record["peak_rss_mb"] + 64)))
        record["efficiency"] = 0.7 * record["time_efficiency"] + 0.3 * record["memory_efficiency"]
    except Exception as error:
        record["status"] = "invalid_output"
        record["errors"].append(str(error))


def family_scores(records):
    families = {}
    for family in sorted({record["family"] for record in records}):
        members = [record for record in records if record["family"] == family]
        summary = {
            "case_ids": [record["case_id"] for record in members],
            "accuracy": float(np.mean([record["accuracy"] for record in members])),
            "failed_cases": sum(record["status"] != "ok" for record in members),
            "total_seconds": sum(record["seconds"] for record in members),
            "mean_seconds": float(np.mean([record["seconds"] for record in members])),
            "mean_peak_rss_mb": float(np.mean([record["peak_rss_mb"] for record in members])),
            "max_peak_rss_mb": max(record["peak_rss_mb"] for record in members),
            "errors": [f"{record['case_id']}: {error}" for record in members for error in record["errors"]],
        }
        for metric in ("channel_rel", "response_rel"):
            valid = [record[metric] for record in members if record[metric] is not None]
            summary["mean_" + metric] = float(np.mean(valid)) if valid else None
            summary["max_" + metric] = max(valid) if valid else None
        families[family] = summary
    return families


def flatten_diagnostics(value, prefix=""):
    flattened = {}
    if isinstance(value, dict):
        for key, item in value.items():
            flattened.update(flatten_diagnostics(item, f"{prefix}.{key}" if prefix else str(key)))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            flattened.update(flatten_diagnostics(item, f"{prefix}[{index}]"))
    else:
        flattened[prefix] = value
    return flattened


def refinement_changes(selected, refined):
    selected = flatten_diagnostics(selected)
    refined = flatten_diagnostics(refined)
    changes = []
    setting = re.compile(r"step|order|point|sample|batch|quad|grid|node|tol|depth|level|degree|rank|cutoff|precision|resolution|mesh|trajector|subdiv|frequency|omega|(^|[._])dt($|[._])")
    ignored = re.compile(r"seed|elapsed|seconds|rss|error|estimate|observ|infidelity|leakage|coherent|norm|mode($|\.)")
    for key in sorted(selected.keys() | refined.keys()):
        before, after = selected.get(key), refined.get(key)
        if before == after or ignored.search(key.lower()):
            continue
        if setting.search(key.lower()) and not isinstance(before, bool) and not isinstance(after, bool):
            changes.append({"setting": key, "selected": before, "refined": after})
        elif key.lower().split(".")[-1] in ("method", "solver", "algorithm", "integrator"):
            if isinstance(before, str) and isinstance(after, str) and before.replace("refined", "").strip(" _-") != after.replace("refined", "").strip(" _-"):
                changes.append({"setting": key, "selected": before, "refined": after})
    return changes


def logged_seeds(reported):
    seeds = set()
    for key, value in flatten_diagnostics(reported.get("diagnostics", {})).items():
        if key.lower().split(".")[-1] in ("seed", "random_seed", "rng_seed"):
            try:
                seed = finite_float(value)
                if seed >= 0 and seed.is_integer() and seed < 2 ** 53:
                    seeds.add(int(seed))
            except (ValueError, TypeError):
                pass
    if "seed" in reported:
        try:
            seed = finite_float(reported["seed"])
            if seed >= 0 and seed.is_integer() and seed < 2 ** 53:
                seeds.add(int(seed))
        except (ValueError, TypeError):
            pass
    return seeds


def memory_difference(selected, no_memory):
    differences = {}
    distinct = False
    for key in ("channel", "k2"):
        difference = float(np.linalg.norm(selected[key] - no_memory[key]))
        scale = max(float(np.linalg.norm(selected[key])), float(np.linalg.norm(no_memory[key])), 1e-8)
        differences[key] = difference
        distinct |= difference > 128 * np.finfo(float).eps * scale
    return bool(distinct), differences


class EvidenceAudit:
    def __init__(self, output, cases, runner):
        self.output = output
        self.cases = cases
        self.runner = runner
        self.checks = []
        self.warnings = []
        self.flags = [{"kind": "manual_scientific_review", "detail": "Artifact consistency cannot establish scientific validity or verify the narrative chronology."}]
        self.tables = {name: [] for name in TABLES}
        self.index = {name: {} for name in TABLES}
        self.artifacts = {}
        self.table_errors = {}
        self.claim_records = []
        self.reruns = []
        self.rerun_arrays = {}

    def check(self, group, name, score, detail):
        record = {"group": group, "check": name, "score": float(score), "passed": bool(score == 1), "detail": detail}
        if score != 1:
            record["failure"] = f"Incomplete evidence check {group}/{name}: {float(score):.6f} of 1"
        self.checks.append(record)

    def table_name(self, name):
        if name in ("results", "ablation", "scaling"):
            name += ".csv"
        if name not in TABLES:
            raise InvalidArtifact(f"Invalid table reference: {name!r}")
        return name

    def artifact(self, relative, case):
        path = contained_path(self.output, relative, directory=True)
        cache_key = (str(path), case.case_id)
        if cache_key not in self.artifacts:
            arrays, measurements = load_process(path, case)
            reported = read_json(contained_path(path, "metrics.json"))
            if not isinstance(reported, dict):
                raise InvalidArtifact("metrics.json must be an object")
            self.artifacts[cache_key] = (arrays, measurements, reported)
        return path, self.artifacts[cache_key]

    def audit_row(self, table, original, row_number):
        row = dict(original)
        record = {"row_number": row_number, "row_id": row.get("row_id", ""), "errors": [], "valid": False}
        errors = record["errors"]
        try:
            if None in row:
                raise InvalidArtifact("CSV row has extra fields")
            if table == "scaling.csv":
                source_id = row.get("source_row") or row.get("result_row") or row.get("row_id")
                source_table = self.table_name(row.get("source_table") or "results.csv")
                source = self.index[source_table].get(source_id)
                if source is not None and source["valid"]:
                    inherited = dict(source["row"])
                    for field in ("case_id", "mode", "artifact"):
                        if row.get(field) and row[field] != inherited[field]:
                            errors.append(f"Scaling reference changes source {field}")
                    inherited.update({key: value for key, value in row.items() if value not in ("", None)})
                    row = inherited
            missing = [name for name in ROW_FIELDS if row.get(name) in (None, "")]
            if missing:
                raise InvalidArtifact(f"Missing row fields: {', '.join(missing)}")
            case = self.cases.get(row["case_id"])
            if case is None:
                raise InvalidArtifact(f"Unknown public case_id: {row['case_id']!r}")
            if row["mode"] not in MODES:
                raise InvalidArtifact(f"Invalid mode: {row['mode']!r}")
            if row["row_id"] in self.index[table]:
                errors.append(f"Duplicate row_id: {row['row_id']}")
            numeric = {}
            for name in SCALARS + RESOURCES:
                try:
                    numeric[name] = finite_float(row[name])
                except Exception as error:
                    errors.append(f"Invalid {name}: {error}")
            if numeric.get("seconds", 0) < 0 or numeric.get("peak_rss_mb", 0) <= 0:
                errors.append("Resources must have seconds >= 0 and peak_rss_mb > 0")
            path, (arrays, measurements, reported) = self.artifact(row["artifact"], case)
            record.update(case_id=case.case_id, mode=row["mode"], artifact=row["artifact"], recomputed=measurements,
                          claimed=numeric, diagnostics=reported.get("diagnostics", {}))
            for name in SCALARS:
                if name in numeric and not agrees(measurements[name], numeric[name]):
                    errors.append(f"CSV {name}={numeric[name]:.12g}, independently recomputed={measurements[name]:.12g}")
            for name in OBSERVABLES:
                try:
                    if not agrees(measurements[name], reported[name]):
                        errors.append(f"metrics.json {name} disagrees with process.npz")
                except Exception as error:
                    errors.append(f"Invalid metrics.json {name}: {error}")
            for name in RESOURCES:
                try:
                    if name in numeric and not agrees(finite_float(reported[name]), numeric[name]):
                        errors.append(f"CSV {name} disagrees with metrics.json")
                except Exception as error:
                    errors.append(f"Invalid metrics.json {name}: {error}")
            for name in ("case_id", "mode"):
                if reported.get(name) != row[name]:
                    errors.append(f"metrics.json {name} does not match row")
            if not isinstance(reported.get("diagnostics"), dict) or not reported["diagnostics"]:
                errors.append("Missing nonempty diagnostics object")
            if table == "scaling.csv":
                for name, expected in (("segments", case.segments), ("dimension", case.dimension)):
                    try:
                        numeric[name] = finite_float(row[name])
                        if numeric[name] != expected:
                            errors.append(f"{name}={numeric[name]} does not match case arrays ({expected})")
                    except Exception as error:
                        errors.append(f"Invalid scaling {name}: {error}")
            record["row"] = {**row, **numeric}
            record["valid"] = not errors
            record["artifact_key"] = (str(path), case.case_id)
        except Exception as error:
            errors.append(str(error))
        self.tables[table].append(record)
        if record["row_id"] and record["row_id"] not in self.index[table]:
            self.index[table][record["row_id"]] = record

    def audit_tables(self):
        for table in TABLES:
            try:
                text = read_bytes(contained_path(self.output, table)).decode("utf-8-sig")
                reader = csv.DictReader(io.StringIO(text))
                fields = reader.fieldnames or []
                if not fields or len(set(fields)) != len(fields):
                    raise InvalidArtifact("Missing or duplicate CSV headers")
                required = ("row_id", "segments", "dimension") if table == "scaling.csv" else ROW_FIELDS
                missing = sorted(set(required) - set(fields))
                if missing:
                    raise InvalidArtifact(f"Missing CSV headers: {', '.join(missing)}")
                for row_number, row in enumerate(reader, 2):
                    if row_number > TABLE_LIMIT + 1:
                        raise InvalidArtifact(f"CSV exceeds {TABLE_LIMIT} rows")
                    self.audit_row(table, row, row_number)
                if not self.tables[table]:
                    raise InvalidArtifact("Empty table")
            except Exception as error:
                self.table_errors[table] = str(error)
            records = self.tables[table]
            verified = sum(record["valid"] for record in records)
            score = verified / max(len(records), 1) if table not in self.table_errors else 0.0
            self.check("tables", table, score, {"verified_rows": verified, "rows": len(records), "error": self.table_errors.get(table)})
        expected = {(case_id, mode) for case_id in self.cases for mode in ("selected", "baseline")}
        actual = {(record.get("case_id"), record.get("mode")) for record in self.tables["results.csv"] if record["valid"]}
        self.check("coverage", "public_selected_and_baseline", len(expected & actual) / len(expected), {"missing": sorted(expected - actual)})
        sizes = {(self.cases[record["case_id"]].segments, self.cases[record["case_id"]].dimension)
                 for record in self.tables["scaling.csv"] if record["valid"]}
        self.check("scaling", "three_measured_problem_sizes", min(1, len(sizes) / 3), {"sizes": sorted(sizes)})
        self.warnings.append("Historical seconds/RSS cannot be reconstructed from process.npz: all rows are checked against metrics.json, and sampled reruns record independent resources including launch overhead.")

    def saved_rows(self, case_id, mode, table=None):
        names = (table,) if table else TABLES
        return [record for name in names for record in self.tables[name]
                if record.get("case_id") == case_id and record.get("mode") == mode and "artifact_key" in record]

    def audit_ablations(self):
        complete = []
        distinct_settings = []
        effects = []
        for case_id, case in self.cases.items():
            if case.description["noise"]["kind"] == "white":
                continue
            selections = {mode: [record for record in self.saved_rows(case_id, mode, "ablation.csv") if record["valid"]]
                          for mode in ("selected", "refined", "no_memory")}
            if not all(selections.values()):
                continue
            records = {mode: candidates[0] for mode, candidates in selections.items()}
            complete.append(case_id)
            changes = refinement_changes(records["selected"]["diagnostics"], records["refined"]["diagnostics"])
            distinct_settings.append({"case_id": case_id, "changes": changes})
            if len(case.arrays["blocks"]) > 2:
                selected_arrays = self.artifacts[records["selected"]["artifact_key"]][0]
                memory_arrays = self.artifacts[records["no_memory"]["artifact_key"]][0]
                selected_arrays = self.rerun_arrays.get((case_id, "selected"), selected_arrays)
                memory_arrays = self.rerun_arrays.get((case_id, "no_memory"), memory_arrays)
                distinct, differences = memory_difference(selected_arrays, memory_arrays)
                effects.append({"case_id": case_id, "distinct": distinct, "differences": differences,
                                "uses_fresh_reruns": (case_id, "selected") in self.rerun_arrays and (case_id, "no_memory") in self.rerun_arrays})
        self.check("ablations", "two_nonwhite_triplets", min(1, len(complete) / 2), {"cases": complete})
        self.check("ablations", "refined_numerical_settings", sum(bool(item["changes"]) for item in distinct_settings) / max(2, len(distinct_settings)), distinct_settings)
        self.check("ablations", "nonzero_memory_effect", any(effect["distinct"] for effect in effects), effects)

    def audit_claims(self):
        memory_claim = False
        validity_claim = False
        texts = []
        try:
            claims = read_json(contained_path(self.output, "claims.json"))
            if not isinstance(claims, list) or not claims or len(claims) > TABLE_LIMIT:
                raise InvalidArtifact("claims.json must be a nonempty bounded list")
        except Exception as error:
            self.check("claims", "quantitative_claims", 0, str(error))
            self.check("claims", "memory_claim", 0, "No verified memory claim")
            self.check("claims", "refinement_or_validity_claim", 0, "No verified refinement/validity claim")
            return texts
        identifiers = set()
        for claim in claims:
            record = {"valid": False, "errors": []}
            try:
                required = ("claim_id", "text", "table", "rows", "metric", "operation", "value")
                if not isinstance(claim, dict) or any(name not in claim for name in required):
                    raise InvalidArtifact("Claim fields are missing")
                record["claim_id"] = claim["claim_id"]
                if not isinstance(claim["claim_id"], str) or not claim["claim_id"] or claim["claim_id"] in identifiers:
                    raise InvalidArtifact("Duplicate or invalid claim_id")
                identifiers.add(claim["claim_id"])
                if not isinstance(claim["text"], str) or not claim["text"].strip():
                    raise InvalidArtifact("Claim text must be nonempty")
                texts.append(("claims.json:" + claim["claim_id"], claim["text"]))
                table = self.table_name(claim["table"])
                operation = claim["operation"]
                expected_count = {"value": 1, "difference": 2, "ratio": 2}.get(operation)
                if expected_count is None or not isinstance(claim["rows"], list) or len(claim["rows"]) != expected_count:
                    raise InvalidArtifact("Invalid operation or source-row count")
                rows = [self.index[table][row_id] for row_id in claim["rows"]]
                if not all(row["valid"] for row in rows):
                    raise InvalidArtifact("Claim references an unverified table row")
                metric = claim["metric"]
                if metric not in SCALARS + RESOURCES + ("segments", "dimension"):
                    raise InvalidArtifact(f"Invalid claim metric: {metric!r}")
                values = [finite_float(row["row"][metric]) for row in rows]
                if operation == "value":
                    computed = values[0]
                elif operation == "difference":
                    computed = values[0] - values[1]
                else:
                    if values[1] == 0:
                        raise InvalidArtifact("Claim ratio has zero denominator")
                    computed = values[0] / values[1]
                record.update(computed=finite_float(computed), claimed=finite_float(claim["value"]))
                if not agrees(computed, claim["value"]):
                    raise InvalidArtifact(f"Claim value {claim['value']} disagrees with source-row {operation}: {computed:.12g}")
                record["valid"] = True
                modes = {row["mode"] for row in rows}
                same_case = len({row["case_id"] for row in rows}) == 1
                nonwhite = self.cases[rows[0]["case_id"]].description["noise"]["kind"] != "white"
                memory_claim |= same_case and nonwhite and modes == {"selected", "no_memory"}
                validity_claim |= same_case and modes == {"selected", "refined"}
                validity_claim |= bool(re.search(r"valid|converg|refin|limitation|approximation", claim["text"], re.I)) and modes == {"selected", "baseline"} and same_case
            except Exception as error:
                record["errors"].append(str(error))
            self.claim_records.append(record)
        self.check("claims", "quantitative_claims", sum(record["valid"] for record in self.claim_records) / len(claims), {"claims": len(claims)})
        self.check("claims", "memory_claim", memory_claim, "Requires verified selected/no_memory rows for the same non-white case")
        self.check("claims", "refinement_or_validity_claim", validity_claim, "Requires a same-case refinement or evidence-linked baseline/selected validity comparison")
        return texts

    def audit_reruns(self):
        for required in ("driven_static", "white_gate"):
            if required not in self.cases:
                raise InfrastructureError(f"Public manifest lacks required evidence-rerun case {required}")
        baseline = min(self.cases.values(), key=lambda case: (case.dimension, case.segments, case.case_id))
        if "calibration_static" in self.cases:
            baseline = self.cases["calibration_static"]
        jobs = [("driven_static", "selected"), ("white_gate", "selected"),
                ("driven_static", "refined"), ("driven_static", "no_memory"), (baseline.case_id, "baseline")]
        for case_id, mode in jobs:
            saved = self.saved_rows(case_id, mode)
            seeds = set()
            for row in saved:
                seeds.update(logged_seeds(self.artifacts[row["artifact_key"]][2]))
            seed = min(seeds) if seeds else None
            if len(seeds) > 1:
                self.warnings.append(f"{case_id}/{mode}: inconsistent logged seeds {sorted(seeds)}; rerunning with {seed}")
            record, arrays = self.runner.run(self.cases[case_id], mode, seed)
            record["comparisons"] = []
            self.reruns.append(record)
            if arrays is not None:
                self.rerun_arrays[(case_id, mode)] = arrays
            seen = set()
            for row in saved:
                if row["artifact_key"] in seen:
                    continue
                seen.add(row["artifact_key"])
                comparison = {"artifact": row["artifact"], "matches": False, "errors": []}
                try:
                    if arrays is None or record["status"] != "ok":
                        raise InvalidArtifact("Rerun did not produce a valid physical process")
                    expected, measurements, reported = self.artifacts[row["artifact_key"]]
                    comparison["channel_rel"] = relative_error(arrays["channel"], expected["channel"])
                    comparison["response_rel"] = relative_error(arrays["k2"], expected["k2"])
                    comparison["matches"] = max(comparison["channel_rel"], comparison["response_rel"]) <= RERUN_RTOL
                    comparison["reported_resources"] = {name: reported.get(name) for name in RESOURCES}
                    if not comparison["matches"]:
                        comparison["errors"].append(f"Saved process does not reproduce within relative {RERUN_RTOL:g}")
                        self.warnings.append(f"{case_id}/{mode}: nonreproducible artifact {row['artifact']}; Monte Carlo variation is possible, but reproducibility is required. Logged seed={seed}; seed environment was supplied when available.")
                    diagnostics_text = json.dumps(reported.get("diagnostics", {})).lower()
                    if seed is None and re.search(r"monte.?carlo|trajector|stochastic|samples|batches", diagnostics_text):
                        self.warnings.append(f"{case_id}/{mode}: stochastic method has no logged seed")
                except Exception as error:
                    comparison["errors"].append(str(error))
                record["comparisons"].append(comparison)
            comparisons = record["comparisons"]
            self.check("reruns", f"{case_id}/{mode}", sum(item["matches"] for item in comparisons) / max(1, len(comparisons)),
                       {"status": record["status"], "artifacts_compared": len(comparisons), "error": "No saved artifact to compare" if not comparisons else None})
            returned_seeds = logged_seeds(record.get("reported_metrics", {}))
            if seed is not None and returned_seeds and seed not in returned_seeds:
                self.warnings.append(f"{case_id}/{mode}: rerun logs seeds {sorted(returned_seeds)}, not requested seed {seed}")
        selected_record = next(record for record in self.reruns if record["case_id"] == "driven_static" and record["mode"] == "selected")
        refined_record = next(record for record in self.reruns if record["case_id"] == "driven_static" and record["mode"] == "refined")
        changes = refinement_changes(selected_record.get("reported_metrics", {}).get("diagnostics", {}), refined_record.get("reported_metrics", {}).get("diagnostics", {}))
        self.check("ablations", "rerun_refinement_settings", bool(changes) and selected_record["status"] == refined_record["status"] == "ok", changes)

    def source_entries(self, document):
        if isinstance(document, dict) and "figures" in document:
            document = document["figures"]
        if isinstance(document, dict):
            return list(document.items())
        if isinstance(document, list):
            entries = []
            for entry in document:
                if not isinstance(entry, dict):
                    raise InvalidArtifact("Figure entry must be an object")
                name = entry.get("file") or entry.get("figure") or entry.get("image") or entry.get("path")
                entries.append((name, entry))
            return entries
        raise InvalidArtifact("sources.json must be a figure mapping or list")

    def audit_figures(self):
        expected = ("figures/primary_result.png", "figures/robustness_or_scaling.png")
        linked = set()
        source_errors = []
        try:
            document = read_json(contained_path(self.output, "figures/sources.json"))
            entries = self.source_entries(document)
            if not entries:
                raise InvalidArtifact("Empty figure source mapping")
            for name, source in entries:
                try:
                    if not isinstance(name, str):
                        raise InvalidArtifact("Missing figure filename")
                    if Path(name).is_absolute() or ".." in Path(name).parts:
                        raise InvalidArtifact(f"Figure path escape rejected: {name!r}")
                    relative = name if name.startswith("figures/") else "figures/" + name
                    image = contained_path(self.output, relative)
                    validate_png(image)
                    references = source.get("sources", source) if isinstance(source, dict) else source
                    if isinstance(references, dict):
                        references = [references]
                    if not isinstance(references, list) or not references:
                        raise InvalidArtifact("Figure must reference table rows")
                    for reference in references:
                        table = self.table_name(reference["table"])
                        rows = reference["rows"]
                        if not isinstance(rows, list) or not rows:
                            raise InvalidArtifact("Figure source rows must be a nonempty list")
                        for row_id in rows:
                            if not self.index[table][row_id]["valid"]:
                                raise InvalidArtifact(f"Figure references unverified row {row_id}")
                    linked.add(relative)
                except Exception as error:
                    source_errors.append(f"{name!r}: {error}")
        except Exception as error:
            source_errors.append(str(error))
        for relative in expected:
            self.check("figures", relative, relative in linked, {"linked": relative in linked, "errors": source_errors})
        self.check("figures", "valid_source_references", not source_errors and bool(linked), {"linked": sorted(linked), "errors": source_errors})

    def audit_report(self, claim_texts):
        try:
            report = read_bytes(contained_path(self.output, "report.md")).decode("utf-8")
            if not report.strip():
                raise InvalidArtifact("Empty report.md")
            self.check("report", "readable_report", 1, "Scientific reasoning and chronology require manual inspection")
            table_links = [name for name in TABLES if name in report]
            artifact_links = [record["artifact"] for rows in self.tables.values() for record in rows if record.get("valid") and record["artifact"] in report]
            row_links = [record["row_id"] for rows in self.tables.values() for record in rows if record.get("valid") and record["row_id"] in report]
            self.check("report", "evidence_links", bool(table_links or artifact_links or row_links), {"tables": table_links, "artifacts": sorted(set(artifact_links)), "rows": sorted(set(row_links))})
            claim_texts = claim_texts + [("report.md", report)]
        except Exception as error:
            self.check("report", "readable_report", 0, str(error))
            self.check("report", "evidence_links", 0, "Report unavailable")
        for source, text in claim_texts:
            for sentence in re.split(r"[.!?\n]", text):
                if re.search(r"gaussian", sentence, re.I) and re.search(r"exact", sentence, re.I):
                    universal = re.search(r"\ball\b|always|every|arbitrary|universal|guarantee|\bany\b", sentence, re.I)
                    negative = re.search(r"\bnot\b|never|isn't|isn’t|doesn't|doesn’t|\bfalse\b|incorrect|non-gaussian", sentence, re.I)
                    if universal and not negative:
                        self.flags.append({"kind": "gaussian_all_exact_claim", "source": source, "excerpt": sentence.strip()[:1000], "detail": "Manual inspection requested; this flag does not reduce the evidence score."})

    def run(self):
        self.audit_tables()
        claim_texts = self.audit_claims()
        self.audit_reruns()
        self.audit_ablations()
        self.audit_figures()
        self.audit_report(claim_texts)
        groups = {group: float(np.mean([check["score"] for check in self.checks if check["group"] == group])) for group in GROUPS}
        score = float(np.mean(list(groups.values())))
        tables = {name: [{key: value for key, value in record.items() if key not in ("row", "artifact_key")} for record in records] for name, records in self.tables.items()}
        return {"score": score, "numerator": score, "denominator": 1, "skipped": False, "groups": groups,
                "checks": self.checks, "tables": tables, "table_errors": self.table_errors,
                "claims": self.claim_records, "reruns": self.reruns,
                "warnings": sorted(set(self.warnings)), "manual_review_flags": self.flags}


def validate_png(path):
    if path.suffix.lower() != ".png":
        raise InvalidArtifact("Figure must have a .png extension")
    payload = read_bytes(path, FILE_LIMIT)
    if not payload.startswith(b"\x89PNG\r\n\x1a\n"):
        raise InvalidArtifact("Invalid PNG signature")
    offset = 8
    kinds = []
    while offset + 12 <= len(payload):
        length = struct.unpack_from(">I", payload, offset)[0]
        kind = payload[offset + 4:offset + 8]
        end = offset + 8 + length
        if end + 4 > len(payload):
            raise InvalidArtifact("Truncated PNG chunk")
        checksum = struct.unpack_from(">I", payload, end)[0]
        if zlib.crc32(payload[offset + 4:end]) & 0xffffffff != checksum:
            raise InvalidArtifact("PNG chunk checksum mismatch")
        if not kinds:
            if kind != b"IHDR" or length != 13:
                raise InvalidArtifact("Missing PNG IHDR")
            width, height = struct.unpack_from(">II", payload, offset + 8)
            if not width or not height or width * height > 40000000:
                raise InvalidArtifact("Invalid or excessive PNG dimensions")
        kinds.append(kind)
        offset = end + 4
        if kind == b"IEND":
            if length or offset != len(payload) or b"IDAT" not in kinds:
                raise InvalidArtifact("Invalid PNG image/end chunks")
            return
    raise InvalidArtifact("Incomplete PNG")


def evaluate(arguments, result):
    output = Path(arguments.output_dir).resolve()
    result.update(output_dir=str(output), sandboxed=not arguments.unsandboxed,
                  limits={"seconds_per_child": TIME_LIMIT, "memory_bytes": MEMORY_LIMIT,
                          "memory_enforcement": "RLIMIT_AS per process plus sampled process-tree RSS",
                          "resource_accounting": "wait4 and process-tree RSS sampling"}, cases=[])
    hidden = load_cases(HERE / "hidden")
    targets = load_private_targets(hidden)
    public = load_cases(HERE.parent / "participant" / "v_01" / "input") if not arguments.skip_evidence else {}
    runner = Runner(output, arguments.unsandboxed)
    for case_id, case in hidden.items():
        target, reference = targets[case_id]
        record, arrays = runner.run(case)
        score_case(case, record, arrays, target, reference)
        result["cases"].append(record)
    families = family_scores(result["cases"])
    family_accuracy = [family["accuracy"] for family in families.values()]
    core = 0.7 * float(np.mean(family_accuracy)) + 0.3 * min(family_accuracy)
    efficiency = float(np.mean([record["efficiency"] for record in result["cases"]]))
    result.update(families=families, core_score=core, efficiency_score=efficiency)
    if arguments.skip_evidence:
        evidence = {"score": 1.0, "numerator": 1.0, "denominator": 1, "skipped": True,
                    "reason": "Operator-requested --skip-evidence; reserved for trusted reference evaluation",
                    "checks": [], "reruns": [], "warnings": ["Evidence was not audited"]}
    else:
        evidence = EvidenceAudit(output, public, runner).run()
    result.update(status="ok", evidence=evidence, evidence_score=evidence["score"],
                  score=0.85 * core + 0.10 * efficiency + 0.05 * evidence["score"],
                  weights={"core": 0.85, "efficiency": 0.10, "evidence": 0.05},
                  child_wall_seconds=sum(record["seconds"] for record in result["cases"] + evidence["reruns"]))


def write_result(path, result):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(result, indent=2, allow_nan=False) + "\n"
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, prefix=".evaluate-", delete=False) as stream:
        temporary = Path(stream.name)
        stream.write(payload)
    try:
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output_dir", metavar="OUTPUT_DIR")
    parser.add_argument("--result", required=True, metavar="RESULT_JSON")
    parser.add_argument("--skip-evidence", action="store_true", help="Trusted-reference use: mark evidence skipped and set it to 1")
    parser.add_argument("--unsandboxed", action="store_true", help="Trusted-reference use only: allow host filesystem/network access")
    arguments = parser.parse_args()
    os.umask(0o077)
    started = time.monotonic()
    result = {"status": "infrastructure_error", "score": None, "errors": []}
    exit_code = 0
    try:
        evaluate(arguments, result)
    except InfrastructureError as error:
        result.update(status="infrastructure_error", score=None)
        result["errors"].append(str(error))
        if error.details is not None:
            result["infrastructure_details"] = error.details
        exit_code = 2
    except Exception as error:
        result.update(status="infrastructure_error", score=None)
        result["errors"].append(f"Unexpected evaluator failure: {type(error).__name__}: {error}")
        result["traceback"] = traceback.format_exc()
        exit_code = 2
    result["runtime_seconds"] = time.monotonic() - started
    try:
        write_result(arguments.result, result)
    except Exception as error:
        print(json.dumps({"status": "infrastructure_error", "score": None, "errors": [f"Cannot write result: {error}"]}), file=sys.stderr)
        return 2
    print(json.dumps({"status": result["status"], "score": result["score"], "result": str(Path(arguments.result).resolve()), "errors": result["errors"]}))
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
