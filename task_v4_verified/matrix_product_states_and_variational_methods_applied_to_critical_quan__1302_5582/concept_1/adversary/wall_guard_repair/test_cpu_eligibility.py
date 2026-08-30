import json
from pathlib import Path
import sys
import tempfile


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "evaluator"))
from sandbox_runner import run_submission


def main():
    with tempfile.TemporaryDirectory(prefix="cpu-eligibility-", dir="/tmp") as directory:
        submission = Path(directory)
        (submission / "solve.py").write_text("import time\nstarted=time.process_time()\nwhile time.process_time()-started < 2.0:\n    pass\n")
        result = run_submission(submission, ROOT / "participant",
                                ROOT / "adversary/wall_guard_repair/cpu_eligibility_check",
                                {"budget_seconds": 1, "wall_seconds": 10})
    assert result["returncode"] == 0 and result["cpu_accounted"], result
    assert result["cpu_seconds"] > 1 and not result["timed_out"], result
    assert not result["process_valid"], "kernel enforcement grace relaxed eligibility"
    report = {"passed": 1, "failed": 0, "result": result}
    (ROOT / "adversary/wall_guard_repair/cpu_eligibility_validation.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"passed": 1, "failed": 0, "cpu_seconds": result["cpu_seconds"]}))


if __name__ == "__main__":
    main()
