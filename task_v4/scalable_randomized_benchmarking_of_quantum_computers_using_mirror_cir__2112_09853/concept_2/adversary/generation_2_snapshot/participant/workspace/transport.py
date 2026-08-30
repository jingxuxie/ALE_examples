import hashlib
import json
import math
import os
from pathlib import Path
import resource
import select
import shutil
import signal
import stat
import subprocess
import sys
import time


class SessionError(ValueError):
    pass


def strict_json(text):
    def unique_object(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise SessionError("duplicate_json_key")
            result[key] = value
        return result

    def invalid_constant(value):
        raise SessionError("nonfinite_json_number")

    return json.loads(text, object_pairs_hook=unique_object, parse_constant=invalid_constant)


def tree_hash(directory):
    digest = hashlib.sha256()
    for path in sorted(Path(directory).rglob("*")):
        if path.is_file():
            digest.update(path.relative_to(directory).as_posix().encode() + b"\0")
            digest.update(path.read_bytes())
    return digest.hexdigest()


def snapshot_submission(submission, destination, policy):
    submission = Path(submission)
    if submission.is_symlink() or not submission.is_dir():
        raise SessionError("submission_must_be_regular_directory")
    policy_path = Path(policy)
    if policy_path.is_absolute() or ".." in policy_path.parts or policy_path.suffix != ".py":
        raise SessionError("policy_must_be_relative_python_file")
    total_bytes = 0
    file_count = 0
    files = []
    for directory, subdirectories, names in os.walk(submission, followlinks=False):
        subdirectories[:] = sorted(name for name in subdirectories if name not in ("__pycache__", ".git"))
        for name in subdirectories:
            if (Path(directory) / name).is_symlink():
                raise SessionError("submission_symlink")
        for name in sorted(names):
            path = Path(directory) / name
            metadata = path.lstat()
            if not stat.S_ISREG(metadata.st_mode) or metadata.st_nlink != 1:
                raise SessionError("submission_nonregular_or_linked_file")
            file_count += 1
            total_bytes += metadata.st_size
            if file_count > 256 or total_bytes > 16777216:
                raise SessionError("submission_size_limit")
            files.append(path)
    destination = Path(destination)
    destination.mkdir(parents=True, exist_ok=False)
    for source in files:
        target = destination / source.relative_to(submission)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
    if not (destination / policy_path).is_file():
        raise SessionError("missing_policy")
    return tree_hash(destination)


def launch_command(submission, policy, isolation):
    interpreter = str(Path(sys.executable).resolve())
    if isolation == "audit":
        return [interpreter, "-E", "-s", "-B", "-u", str(Path(submission) / policy)]
    executable = shutil.which("bwrap")
    if not executable:
        raise SessionError("bubblewrap_unavailable_use_main_allowlisted_runner")
    if not interpreter.startswith("/usr/"):
        raise SessionError("interpreter_outside_readonly_runtime")
    command = [executable, "--die-with-parent", "--new-session", "--unshare-all",
               "--ro-bind", "/usr", "/usr"]
    for directory in ("/bin", "/lib", "/lib64"):
        if Path(directory).exists():
            command.extend(["--ro-bind", directory, directory])
    command.extend(["--dir", "/etc"])
    for filename in ("/etc/ld.so.cache", "/etc/localtime", "/etc/alternatives"):
        if Path(filename).exists():
            command.extend(["--ro-bind", filename, filename])
    command.extend(["--proc", "/proc", "--dev", "/dev", "--tmpfs", "/tmp",
                    "--ro-bind", str(Path(submission).resolve()), "/submission",
                    "--chdir", "/submission", "--", interpreter,
                    "-E", "-s", "-B", "-u", "/submission/" + policy])
    return command


def child_limits():
    resource.setrlimit(resource.RLIMIT_CPU, (60, 61))
    resource.setrlimit(resource.RLIMIT_AS, (1536 * 1024 * 1024, 1536 * 1024 * 1024))
    resource.setrlimit(resource.RLIMIT_FSIZE, (262144, 262144))
    resource.setrlimit(resource.RLIMIT_NOFILE, (64, 64))
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))


def run_episode(episode, command, directory, stderr_path, wall_seconds=90, transcript_path=None):
    started = time.monotonic()
    deadline = started + wall_seconds
    usage_before = resource.getrusage(resource.RUSAGE_CHILDREN)
    environment = {"PATH": "/usr/bin:/bin", "HOME": "/tmp", "LANG": "C.UTF-8",
                   "OPENBLAS_NUM_THREADS": "1", "OMP_NUM_THREADS": "1",
                   "MKL_NUM_THREADS": "1", "NUMEXPR_NUM_THREADS": "1",
                   "PYTHONDONTWRITEBYTECODE": "1"}
    process = None
    record = {"valid": False, "reason": "not_started", "shots_used": 0, "experiments": 0}
    transcript = hashlib.sha256()
    transcript_handle = open(transcript_path, "w") if transcript_path else None

    def log_message(direction, message):
        line = json.dumps({"direction": direction, "message": message}, sort_keys=True, allow_nan=False)
        transcript.update(line.encode() + b"\n")
        if transcript_handle:
            transcript_handle.write(line + "\n")

    try:
        with open(stderr_path, "wb") as stderr_file:
            process = subprocess.Popen(command, cwd=directory, stdin=subprocess.PIPE,
                                       stdout=subprocess.PIPE, stderr=stderr_file, env=environment,
                                       start_new_session=True, preexec_fn=child_limits, bufsize=0)
            os.set_blocking(process.stdin.fileno(), False)
            os.set_blocking(process.stdout.fileno(), False)
            buffered = bytearray()

            def send(message):
                log_message("evaluator", message)
                payload = memoryview((json.dumps(message, allow_nan=False) + "\n").encode())
                while payload:
                    remaining = deadline - time.monotonic()
                    if remaining <= 0:
                        raise SessionError("wall_time_limit")
                    readable, writable, exceptional = select.select([], [process.stdin], [], remaining)
                    if not writable:
                        raise SessionError("wall_time_limit")
                    written = os.write(process.stdin.fileno(), payload)
                    payload = payload[written:]

            def receive():
                while True:
                    newline = buffered.find(b"\n")
                    if newline > 32768 or (newline < 0 and len(buffered) > 32768):
                        raise SessionError("line_size_limit")
                    if newline >= 0:
                        line = bytes(buffered[:newline])
                        del buffered[:newline + 1]
                        message = strict_json(line.decode("utf-8"))
                        log_message("participant", message)
                        return message
                    remaining = deadline - time.monotonic()
                    if remaining <= 0:
                        raise SessionError("wall_time_limit")
                    readable, writable, exceptional = select.select([process.stdout], [], [], remaining)
                    if not readable:
                        raise SessionError("wall_time_limit")
                    chunk = os.read(process.stdout.fileno(), 4096)
                    if not chunk:
                        raise SessionError("participant_eof_before_final")
                    buffered.extend(chunk)

            send(episode.hello())
            while episode.phase != "finished":
                message = receive()
                response = episode.handle(message)
                send(response)
            process.stdin.close()
            if buffered:
                raise SessionError("output_after_final")
            exit_deadline = deadline
            while True:
                remaining = exit_deadline - time.monotonic()
                if remaining <= 0:
                    raise SessionError("did_not_exit_after_final")
                readable, writable, exceptional = select.select([process.stdout], [], [], remaining)
                if readable:
                    extra = os.read(process.stdout.fileno(), 4096)
                    if extra:
                        raise SessionError("output_after_final")
                    break
            process.wait(timeout=max(0.01, exit_deadline - time.monotonic()))
            if process.returncode != 0:
                raise SessionError("nonzero_exit")
            record.update(episode.metrics())
            record.update(valid=True, reason="ok")
    except (ValueError, TypeError, OSError, UnicodeError, RecursionError,
            subprocess.SubprocessError, OverflowError) as exception:
        record["reason"] = str(exception)[:240] or type(exception).__name__
    finally:
        if process is not None:
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            process.wait()
            for stream in (process.stdin, process.stdout):
                if stream and not stream.closed:
                    stream.close()
        if transcript_handle:
            transcript_handle.close()
    usage_after = resource.getrusage(resource.RUSAGE_CHILDREN)
    record.update(shots_used=episode.shots_used, experiments=episode.experiments,
                  wall_seconds=time.monotonic() - started,
                  cpu_seconds=usage_after.ru_utime + usage_after.ru_stime -
                              usage_before.ru_utime - usage_before.ru_stime,
                  peak_rss_kib=usage_after.ru_maxrss,
                  transcript_sha256=transcript.hexdigest())
    if record["cpu_seconds"] > 60.25:
        record.update(valid=False, reason="aggregate_cpu_limit")
    return record


def aggregate(records, isolated):
    families = {}
    for record in records:
        families.setdefault(record["family"], []).append(record)
    family_results = {}
    for family, members in families.items():
        if all(member["valid"] for member in members):
            mean_squared = sum(member["normalized_mse"] for member in members) / len(members)
            family_results[family] = {"score": 1.0 / (1.0 + mean_squared),
                                      "normalized_rmse": math.sqrt(mean_squared),
                                      "episodes": len(members)}
        else:
            family_results[family] = {"score": 0.0, "normalized_rmse": None,
                                      "episodes": len(members)}
    average = sum(value["score"] for value in family_results.values()) / max(1, len(family_results))
    worst = min((value["score"] for value in family_results.values()), default=0.0)
    valid = bool(records) and all(record["valid"] for record in records)
    accuracy_passed = valid and average >= 0.5 and worst >= 1.0 / 2.5625
    reason = "fixed_targets_met" if accuracy_passed else "accuracy_target_not_met"
    if not valid:
        reason = "invalid_episode: " + next((record["reason"] for record in records if not record["valid"]), "no_episodes")
    elif not isolated:
        reason = "uncertified_audit_only_run; " + reason
    utilization = max((max(record["shots_used"] / 12000, record["experiments"] / 768,
                           record["wall_seconds"] / 90, record["cpu_seconds"] / 60)
                       for record in records), default=0.0)
    return {"valid": valid, "passed": accuracy_passed and isolated, "accuracy_passed": accuracy_passed,
            "reason": reason, "core_score": average, "average_family_score": average,
            "worst_family_score": worst, "families": family_results,
            "runtime_resource_score": max(0.0, 1.0 - 0.5 * min(1.0, utilization)) if valid else 0.0,
            "resources": {"total_shots": sum(record["shots_used"] for record in records),
                          "total_experiments": sum(record["experiments"] for record in records),
                          "wall_seconds": sum(record["wall_seconds"] for record in records),
                          "cpu_seconds": sum(record["cpu_seconds"] for record in records),
                          "peak_rss_kib": max((record["peak_rss_kib"] for record in records), default=0)},
            "episodes": records}
