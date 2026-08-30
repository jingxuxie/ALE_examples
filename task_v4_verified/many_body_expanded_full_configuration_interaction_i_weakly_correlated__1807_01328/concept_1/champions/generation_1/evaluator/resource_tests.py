import json
import subprocess
import tempfile
from pathlib import Path

from evaluate import ROOT, sandbox_command


def run_case(source, options):
    with tempfile.TemporaryDirectory(prefix="mbe_resource_test_") as temporary:
        directory = Path(temporary)
        (directory / "solution.py").write_text(source)
        command = sandbox_command(directory)
        position = max(index for index, value in enumerate(command) if value == "/resource_guard.py") + 1
        command[position:position] = options
        process = subprocess.run(command, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                                 stderr=subprocess.PIPE, text=True, timeout=90)
        lines = process.stderr.splitlines()
        if not lines or not lines[-1].startswith("MBE_GUARD_RESOURCE "):
            raise RuntimeError("resource guard unavailable: " + process.stderr)
        report = json.loads(lines[-1].split(" ", 1)[1])
        report["returncode"] = process.returncode
        return report


def main():
    forked_work = ("import os, time\n"
                   "child = os.fork()\n"
                   "started = time.process_time()\n"
                   "while time.process_time() - started < .2: pass\n"
                   "if child: os.waitpid(child, 0)\n")
    accounting = run_case(forked_work, ["--cpu", "2"])
    assert accounting["reason"] == "ok" and accounting["cpu_seconds"] > 0.35, accounting
    cpu_limit = run_case(forked_work, ["--cpu", "0.12"])
    assert cpu_limit["reason"] == "aggregate_cpu_limit" and cpu_limit["returncode"] != 0, cpu_limit
    memory_limit = run_case("import time\ndata = bytearray(100 * 1024 ** 2)\ntime.sleep(.5)\n", ["--memory", str(64 * 1024 ** 2)])
    assert memory_limit["reason"] == "aggregate_memory_limit", memory_limit
    wall_limit = run_case("import time\ntime.sleep(2)\n", ["--wall", "0.1"])
    assert wall_limit["reason"] == "guard_wall_limit", wall_limit
    report = {"passed": True, "forked_cpu_accounting": accounting, "cpu_limit": cpu_limit,
              "memory_limit": memory_limit, "wall_limit": wall_limit}
    (ROOT / "evaluator/hidden/resource_validation.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
