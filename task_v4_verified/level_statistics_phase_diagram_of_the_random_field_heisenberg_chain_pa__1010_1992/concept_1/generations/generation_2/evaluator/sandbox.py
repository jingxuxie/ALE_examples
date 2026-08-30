import ctypes
import json
import os
from pathlib import Path
import signal
import selectors
import subprocess
import tempfile
import time


def affinity_filter(destination):
    library = ctypes.CDLL("libseccomp.so.2")
    library.seccomp_init.argtypes = [ctypes.c_uint32]
    library.seccomp_init.restype = ctypes.c_void_p
    library.seccomp_release.argtypes = [ctypes.c_void_p]
    library.seccomp_syscall_resolve_name.argtypes = [ctypes.c_char_p]
    library.seccomp_syscall_resolve_name.restype = ctypes.c_int
    library.seccomp_rule_add.argtypes = [ctypes.c_void_p, ctypes.c_uint32, ctypes.c_int, ctypes.c_uint]
    library.seccomp_export_bpf.argtypes = [ctypes.c_void_p, ctypes.c_int]
    context = library.seccomp_init(0x7fff0000)
    if not context:
        raise RuntimeError("Cannot initialize resource filter")
    handle = destination.open("w+b")
    try:
        syscall = library.seccomp_syscall_resolve_name(b"sched_setaffinity")
        if syscall < 0 or library.seccomp_rule_add(context, 0x00050001, syscall, 0):
            raise RuntimeError("Cannot create CPU-affinity filter")
        if library.seccomp_export_bpf(context, handle.fileno()):
            raise RuntimeError("Cannot export CPU-affinity filter")
        handle.seek(0)
        return handle
    except Exception:
        handle.close()
        raise
    finally:
        library.seccomp_release(context)


def run_submission(submission, inputs, timeout=12, memory_mb=2048, participant=None,
                   streaming=False, startup_timeout=30):
    submission = Path(submission).resolve()
    if not (submission / "predict.py").is_file():
        raise ValueError("Submission must contain predict.py")
    with tempfile.TemporaryDirectory(prefix="palhuse_eval_") as temporary:
        temporary = Path(temporary)
        input_dir, output_dir = temporary / "input", temporary / "output"
        input_dir.mkdir()
        output_dir.mkdir()
        if not streaming:
            (input_dir / "cases.json").write_text(json.dumps(inputs, allow_nan=False))
        command = ["bwrap", "--unshare-all", "--die-with-parent", "--new-session",
                   "--clearenv", "--ro-bind", "/usr", "/usr",
                   "--ro-bind", "/lib", "/lib", "--ro-bind", "/lib64", "/lib64",
                   "--ro-bind", "/etc/alternatives", "/etc/alternatives",
                   "--ro-bind", "/etc/ld.so.cache", "/etc/ld.so.cache",
                   "--proc", "/proc", "--dev", "/dev", "--tmpfs", "/tmp",
                   "--ro-bind", str(submission), "/submission",
                   "--ro-bind", str(input_dir), "/input", "--bind", str(output_dir), "/output",
                   "--setenv", "PATH", "/usr/bin:/bin", "--setenv", "HOME", "/tmp",
                   "--setenv", "PYTHONDONTWRITEBYTECODE", "1",
                   "--setenv", "PYTHONHASHSEED", "0"]
        for variable in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS",
                         "BLIS_NUM_THREADS", "NUMEXPR_NUM_THREADS", "OMP_THREAD_LIMIT"):
            command.extend(["--setenv", variable, "4"])
        if participant is not None:
            command.extend(["--ro-bind", str(Path(participant).resolve()), "/participant"])
        filter_handle = affinity_filter(temporary / "affinity.bpf")
        command.extend(["--seccomp", str(filter_handle.fileno())])
        command.extend(["--chdir", "/submission", "/usr/bin/prlimit",
                        "--as=" + str(memory_mb * 1024 * 1024),
                        "--cpu=" + str(max(4, int((timeout + startup_timeout) * 4) + 2)),
                        "--fsize=67108864", "--nofile=128", "--",
                        "/usr/bin/python3", "/submission/predict.py"])
        if not streaming:
            command.extend(["--input", "/input/cases.json", "--output", "/output/predictions.json"])
        cpus = sorted(os.sched_getaffinity(0))[:4]
        command = ["taskset", "--cpu-list", ",".join(map(str, cpus))] + command
        started = time.monotonic()
        startup_seconds = 0.0
        response = None
        phase = "startup" if streaming else "batch"
        with (temporary / "stdout").open("wb") as stdout, (temporary / "stderr").open("wb") as stderr:
            process = subprocess.Popen(command, stdin=subprocess.PIPE if streaming else subprocess.DEVNULL,
                                       stdout=subprocess.PIPE if streaming else stdout,
                                       stderr=stderr, start_new_session=True,
                                       pass_fds=(filter_handle.fileno(),))
            filter_handle.close()
            try:
                if streaming:
                    selector = selectors.DefaultSelector()
                    selector.register(process.stdout, selectors.EVENT_READ)
                    ready = b""
                    while b"\n" not in ready:
                        remaining = startup_timeout - (time.monotonic() - started)
                        if remaining <= 0 or not selector.select(remaining):
                            raise subprocess.TimeoutExpired(command, startup_timeout)
                        chunk = os.read(process.stdout.fileno(), 4096)
                        if not chunk:
                            error_text = (temporary / "stderr").read_text(errors="replace")[-4000:]
                            raise ValueError("Prediction process exited before READY: " + error_text)
                        ready += chunk
                        if len(ready) > 64:
                            raise ValueError("Expected a single READY line")
                    selector.close()
                    if ready.strip() != b"READY":
                        raise ValueError("Expected a single READY line")
                    startup_seconds = time.monotonic() - started
                    encoded = (json.dumps(inputs, allow_nan=False) + "\n").encode()
                    inference_started = time.monotonic()
                    phase = "inference"
                    response, unused = process.communicate(encoded, timeout=timeout)
                    returncode = process.returncode
                    elapsed = time.monotonic() - inference_started
                else:
                    returncode = process.wait(timeout=timeout)
                    elapsed = time.monotonic() - started
                timed_out = False
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL)
                returncode = process.wait()
                timed_out = True
                elapsed = time.monotonic() - started - startup_seconds
            except Exception:
                if process.poll() is None:
                    os.killpg(process.pid, signal.SIGKILL)
                    process.wait()
                raise
        error = (temporary / "stderr").read_text(errors="replace")[-4000:]
        if returncode or timed_out:
            raise RuntimeError(json.dumps({"returncode": returncode, "timeout": timed_out,
                                           "seconds": elapsed, "phase": phase, "stderr": error}))
        if streaming:
            if len(response) > 16000000:
                raise ValueError("Prediction response is too large")
            result = json.loads(response)
        else:
            result_path = output_dir / "predictions.json"
            if not result_path.is_file() or result_path.is_symlink() or result_path.stat().st_size > 16000000:
                raise ValueError("Missing or invalid predictions.json")
            result = json.loads(result_path.read_text())
        return result, {"wall_seconds": elapsed, "wall_limit_seconds": timeout,
                        "address_space_mb": memory_mb, "threads": 4, "cpu_affinity": cpus,
                        "cpu_affinity_expansion": "seccomp denied",
                        "startup_seconds": startup_seconds, "startup_limit_seconds": startup_timeout,
                        "total_seconds": time.monotonic() - started, "streaming": streaming,
                        "network": "unshared", "filesystem": "explicit allowlist"}
