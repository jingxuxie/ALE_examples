import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "evaluator"))
from evaluate import run_episode


def main():
    episode = json.loads((ROOT / "participant/input/training.json").read_text())["episodes"][0]
    results = {}
    for mode in ("burn", "overcpu", "isolation", "budget", "boolean", "nan", "forged_meter"):
        result = run_episode(episode, ROOT / "adversary/probes", ["/usr/bin/python3", "/submission/worker.py", mode],
                             cpu_limit=2 if mode == "overcpu" else 60)
        results[mode] = result
        print(mode, result, flush=True)
    assert results["burn"]["valid"] and 2.0 <= results["burn"]["cpu_seconds"] <= 3.0
    assert not results["overcpu"]["valid"] and results["overcpu"]["cpu_seconds"] >= 1.8
    assert results["isolation"]["valid"]
    assert all(not results[mode]["valid"] for mode in ("budget", "boolean", "nan", "forged_meter"))
    (ROOT / "adversary/protocol_report.json").write_text(json.dumps({"passed": True, "results": results}, indent=2) + "\n")


if __name__ == "__main__":
    main()
