import sys

sys.dont_write_bytecode = True

import argparse
import hashlib
import json
from pathlib import Path
import shutil


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "evaluator"))
from evaluate import aggregate, run_episode
from validate_science import check_frozen


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--policy", choices=("robust", "adaptive", "uniform", "weak"), required=True)
    parser.add_argument("--run-label")
    arguments = parser.parse_args()
    label = arguments.run_label or arguments.policy
    check_frozen()
    episodes = json.loads((ROOT / "evaluator/hidden/episodes.json").read_text())["episodes"]
    results = []
    for episode in episodes:
        leaf = ROOT / "adversary/runtime" / label / episode["id"] / "submission"
        leaf.mkdir(parents=True, exist_ok=False)
        if arguments.policy == "weak":
            shutil.copyfile(ROOT / "participant/baseline/solution.py", leaf / "solution.py")
            command = ["/usr/bin/python3", "/submission/solution.py"]
        else:
            for name in ("solution.py", "local_model.py"):
                shutil.copyfile(ROOT / "adversary/portfolio" / name, leaf / name)
            command = ["/usr/bin/python3", "/submission/solution.py", "--policy", arguments.policy]
        result = run_episode(episode, leaf, command)
        results.append(result)
        report = aggregate(results)
        report.update({"official_suite": False, "draft_qualification_only": True, "fresh_agent": False,
                       "complete_qualification": len(results) == 12,
                       "source_sha256": hashlib.sha256((leaf / "solution.py").read_bytes()).hexdigest()})
        (ROOT / "adversary/validation" / (label + "_report.json")).write_text(json.dumps(report, indent=2) + "\n")
        print(json.dumps(result), flush=True)


if __name__ == "__main__":
    main()
