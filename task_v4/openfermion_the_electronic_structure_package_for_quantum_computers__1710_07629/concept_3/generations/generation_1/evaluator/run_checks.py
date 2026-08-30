"""Run and persist the isolation and evaluator regression suite."""

import io
import json
from pathlib import Path
import time
import unittest


def main():
    root = Path(__file__).resolve().parents[1]
    stream = io.StringIO()
    started = time.perf_counter()
    suite = unittest.defaultTestLoader.discover(str(root / "evaluator"), pattern="test_*.py")
    result = unittest.TextTestRunner(stream=stream, verbosity=2).run(suite)
    report = {"tests_run": result.testsRun, "failures": len(result.failures),
              "errors": len(result.errors), "skipped": len(result.skipped),
              "passed": result.wasSuccessful(), "wall_seconds": time.perf_counter() - started}
    (root / "adversary/test_report.json").write_text(json.dumps(report, indent=2) + "\n")
    (root / "adversary/test_log.txt").write_text(stream.getvalue())
    print(stream.getvalue())
    print(json.dumps(report, indent=2))
    raise SystemExit(0 if result.wasSuccessful() else 1)


if __name__ == "__main__":
    main()
