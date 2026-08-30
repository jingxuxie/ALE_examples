import json
from pathlib import Path
import sys
import tempfile


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "evaluator"))
from runner import run_solution


def main():
    source = ("import time,json,sys\n"
              "started=time.process_time()\n"
              "while time.process_time()-started<7.3: pass\n"
              "json.dump({'nodes':[0,1,2]},open(sys.argv[2],'w'))\n")
    with tempfile.TemporaryDirectory(dir=ROOT / "adversary") as directory:
        solution = Path(directory) / "solution.py"
        solution.write_text(source)
        output, timing = run_solution(solution, "{}")
    assert output == {"nodes": [0, 1, 2]}
    assert 7.2 <= timing["cpu_seconds"] < 8.0
    report = {"passed": True, "test": "near-budget single-process CPU burn under the actual scoring sandbox",
              "timing": timing}
    (ROOT / "adversary" / "resource_budget_probe.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
