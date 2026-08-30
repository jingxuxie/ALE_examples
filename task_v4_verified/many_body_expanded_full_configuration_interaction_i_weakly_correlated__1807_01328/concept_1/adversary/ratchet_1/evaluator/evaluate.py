import argparse
import json
import resource
import shutil
import sys
import tempfile
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(1, str(ROOT / "participant/workspace"))
from trusted_protocol import run_policy, summarize


def limits():
    resource.setrlimit(resource.RLIMIT_CPU, (120, 125))
    resource.setrlimit(resource.RLIMIT_AS, (2 * 1024 ** 3, 2 * 1024 ** 3))
    resource.setrlimit(resource.RLIMIT_FSIZE, (128 * 1024 ** 2, 128 * 1024 ** 2))
    resource.setrlimit(resource.RLIMIT_NOFILE, (128, 128))


def sandbox_command(submission):
    if not shutil.which("bwrap"):
        raise RuntimeError("bwrap is required; refusing unsandboxed hidden evaluation")
    command = ["bwrap", "--die-with-parent", "--unshare-all", "--as-pid-1", "--new-session", "--cap-drop", "ALL", "--clearenv"]
    for directory in ("/usr", "/bin", "/lib", "/lib64"):
        if Path(directory).exists():
            command += ["--ro-bind", directory, directory]
    for filename in ("/etc/ld.so.cache", "/etc/alternatives"):
        if Path(filename).exists():
            command += ["--ro-bind", filename, filename]
    command += ["--proc", "/proc", "--dev", "/dev", "--tmpfs", "/tmp",
                "--ro-bind", str(submission), "/submission",
                "--ro-bind", str(ROOT / "participant"), "/participant",
                "--ro-bind", str(ROOT / "evaluator/resource_guard.py"), "/resource_guard.py",
                "--chdir", "/submission"]
    for name, value in {"PATH": "/usr/bin:/bin", "HOME": "/tmp", "TMPDIR": "/tmp",
                        "PYTHONPATH": "/participant/workspace", "PYTHONDONTWRITEBYTECODE": "1",
                        "OPENBLAS_NUM_THREADS": "1", "OMP_NUM_THREADS": "1", "MKL_NUM_THREADS": "1"}.items():
        command += ["--setenv", name, value]
    return command + ["--", "/usr/bin/python3", "/resource_guard.py", "/usr/bin/python3", "/submission/solution.py"]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--submission", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--cases", type=Path)
    parser.add_argument("--models", type=Path)
    arguments = parser.parse_args()
    started = time.monotonic()
    try:
        submission = arguments.submission.resolve(strict=True)
        if not (submission / "solution.py").is_file():
            raise ValueError("submission must contain solution.py")
        if any(path.is_symlink() for path in submission.rglob("*")):
            raise ValueError("submission symlinks are forbidden")
        if sum(path.stat().st_size for path in submission.rglob("*") if path.is_file()) > 128 * 1024 ** 2:
            raise ValueError("submission exceeds 128 MiB")
        hidden = ROOT / "evaluator/hidden"
        tables = np.load(arguments.cases or hidden / "cases.npz", allow_pickle=False)["energies"]
        models = json.loads((arguments.models or hidden / "models.json").read_text())
        with tempfile.TemporaryFile() as error_log:
            try:
                records, elapsed = run_policy(sandbox_command(submission), models, tables, wall_seconds=600, preexec_fn=limits, stderr=error_log)
            except Exception as error:
                error_log.seek(0)
                detail = error_log.read().decode("utf-8", errors="replace")[-6000:]
                raise RuntimeError(str(error) + "; worker diagnostics: " + detail) from error
            error_log.seek(0)
            diagnostic_lines = error_log.read().decode("utf-8", errors="replace").splitlines()
        if not diagnostic_lines or not diagnostic_lines[-1].startswith("MBE_GUARD_RESOURCE "):
            raise RuntimeError("missing trusted namespace resource accounting")
        measured = json.loads(diagnostic_lines[-1].split(" ", 1)[1])
        report = summarize(records, elapsed)
        report["cpu_seconds"] = measured["cpu_seconds"]
        report["peak_policy_rss_bytes"] = measured["peak_rss_bytes"]
        report["resource_accounting"] = "trusted private-PID-namespace supervisor; includes descendants"
        if measured["reason"] != "ok":
            report.update(passed=False, resource_score=0.0, reason=measured["reason"])
        report["isolation"] = "bubblewrap; no hidden paths; no network; private tmp and pid namespaces"
        report["generation"] = 2
        report["diagnostic_only"] = False
        report["limits"] = {"cpu_seconds": 120, "wall_seconds": 600, "memory_bytes": 2147483648,
                            "query_cost_per_system": 160, "submission_bytes": 134217728}
    except Exception as error:
        report = summarize([], time.monotonic() - started, valid=False, reason=f"{type(error).__name__}: {error}")
    if arguments.output:
        arguments.output.parent.mkdir(parents=True, exist_ok=True)
        arguments.output.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({key: value for key, value in report.items() if key != "records"}, indent=2))


if __name__ == "__main__":
    main()
