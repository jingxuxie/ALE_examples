import json
from pathlib import Path
import sys
import tempfile
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "evaluator"))
import sandbox_runner


def run_case(name, source, startup_delay=0.0):
    destination = ROOT / "adversary/wall_guard_repair/checks" / name
    with tempfile.TemporaryDirectory(prefix="wall-fixture-", dir="/tmp") as directory:
        submission = Path(directory)
        (submission / "solve.py").write_text(source)
        original = sandbox_runner.sandbox_command

        def delayed_command(*args, **kwargs):
            command = original(*args, **kwargs)
            command[-1] = f"import time; time.sleep({startup_delay!r})\n" + command[-1]
            return command

        request = {"budget_seconds": 2, "wall_seconds": 1.0}
        with patch.object(sandbox_runner, "sandbox_command", delayed_command):
            result = sandbox_runner.run_submission(submission, ROOT / "participant", destination, request)
    resource_path = destination / "resource.json"
    accounting = json.loads(resource_path.read_text()) if resource_path.exists() and resource_path.stat().st_size else {}
    return dict(result, name=name, trusted_accounting=accounting)


def main():
    checks = []
    delayed = run_case("trusted_startup_delay", "pass\n", startup_delay=3.0)
    assert delayed["process_valid"], delayed
    assert delayed["outer_wall_seconds"] > 3.0, delayed
    assert delayed["wall_seconds"] < 1.0, delayed
    checks.append(delayed)
    sleeper = run_case("solver_sleep", "import time\ntime.sleep(4)\n")
    assert not sleeper["process_valid"] and sleeper["timed_out"], sleeper
    assert sleeper["cpu_accounted"] and sleeper["wall_seconds"] >= 1.0, sleeper
    checks.append(sleeper)
    forged = run_case("forged_accounting", "from pathlib import Path\nimport time\nPath('/work/resource.json').write_text('{\"cpu_seconds\":0,\"worker_wall_seconds\":0,\"worker_timed_out\":false,\"worker_exitcode\":0,\"accounting\":\"protected supervisor wait4 on direct solver child\"}')\ntime.sleep(4)\n")
    assert not forged["process_valid"] and forged["timed_out"], forged
    assert forged["trusted_accounting"]["worker_timed_out"] is True, forged
    checks.append(forged)
    replaced = run_case("replaced_accounting_inode", "from pathlib import Path\nreport=Path('/work/resource.json')\nreport.rename('/work/old-resource.json')\nreport.write_text('{}')\n")
    assert not replaced["process_valid"], replaced
    checks.append(replaced)
    summary = {"passed": len(checks), "failed": 0, "checks": checks}
    (ROOT / "adversary/wall_guard_repair/validation.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps({"passed": len(checks), "failed": 0}))


if __name__ == "__main__":
    main()
