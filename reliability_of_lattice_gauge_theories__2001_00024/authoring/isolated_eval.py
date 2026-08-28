import json
import hashlib
import os
import pathlib
import signal
import subprocess
import tempfile
import time


def run_solver(submission, participant, case, timeout=120, memory_gib=6, startup_grace=0):
    submission = pathlib.Path(submission).resolve()
    participant = pathlib.Path(participant).resolve()
    worker = pathlib.Path(__file__).resolve().with_name("eval_worker.py")
    if not (submission / "solver.py").is_file():
        return {"ok": False, "error": "missing solver.py", "seconds": 0.0, "max_rss_kib": 0}
    with tempfile.TemporaryDirectory(prefix=".evaluation-", dir=submission) as temporary:
        case_path = pathlib.Path(temporary) / "case.json"
        case_path.write_text(json.dumps(case, allow_nan=False))
        command = ["bwrap", "--unshare-all", "--die-with-parent", "--new-session"]
        for directory in ("/usr", "/bin", "/lib", "/lib64", "/etc"):
            if pathlib.Path(directory).exists():
                command.extend(["--ro-bind", directory, directory])
        command.extend(["--proc", "/proc", "--dev", "/dev", "--tmpfs", "/tmp",
                        "--ro-bind", str(participant), str(participant),
                        "--bind", str(submission), str(submission),
                        "--ro-bind", str(worker), "/tmp/eval_worker.py",
                        "--ro-bind", str(case_path), "/tmp/case.json",
                        "--chdir", str(submission)])
        environment = {"PATH": "/usr/local/bin:/usr/bin:/bin", "HOME": "/tmp",
                       "LANG": "C.UTF-8", "OPENBLAS_NUM_THREADS": "1",
                       "OMP_NUM_THREADS": "1", "MKL_NUM_THREADS": "1",
                       "NUMBA_NUM_THREADS": "1", "NUMBA_CACHE_DIR": "/tmp/numba"}
        available_cpus = sorted(os.sched_getaffinity(0))
        case_hash = int(hashlib.sha256(json.dumps(case, sort_keys=True).encode()).hexdigest()[:8], 16)
        cpu = available_cpus[(case_hash + os.getpid()) % len(available_cpus)]
        command.extend(["--", "/usr/bin/python3", "/tmp/eval_worker.py", str(submission),
                        "/tmp/case.json", str(int(memory_gib * 1024**3)), str(cpu), str(timeout)])
        start = time.monotonic()
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                   text=True, env=environment, start_new_session=True)
        try:
            stdout, stderr = process.communicate(timeout=timeout + startup_grace)
        except subprocess.TimeoutExpired:
            os.killpg(process.pid, signal.SIGKILL)
            stdout, stderr = process.communicate()
            return {"ok": False, "error": "case wall-time limit exceeded", "seconds": time.monotonic() - start,
                    "max_rss_kib": None, "timeout": True, "stderr": stderr[-3000:]}
        if process.returncode:
            if "bwrap:" in stderr:
                raise RuntimeError("evaluation isolation infrastructure failed: " + stderr[-3000:])
            if process.returncode in (-signal.SIGXCPU, 128 + signal.SIGXCPU):
                return {"ok": False, "error": "case worker CPU-time limit exceeded", "timeout": True,
                        "seconds": time.monotonic() - start, "max_rss_kib": None, "stderr": stderr[-3000:]}
            return {"ok": False, "error": "solver exited " + str(process.returncode),
                    "seconds": time.monotonic() - start, "max_rss_kib": None, "stderr": stderr[-5000:]}
        try:
            result = json.loads(stdout)
        except (ValueError, TypeError) as error:
            return {"ok": False, "error": "invalid solver output: " + str(error),
                    "seconds": time.monotonic() - start, "max_rss_kib": None, "stderr": stderr[-3000:]}
        result["wall_seconds"] = time.monotonic() - start
        if stderr:
            result["stderr"] = stderr[-3000:]
        return result
