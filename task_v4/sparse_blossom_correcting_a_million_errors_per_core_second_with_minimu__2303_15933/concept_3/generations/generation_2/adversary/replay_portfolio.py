import sys

sys.dont_write_bytecode = True

import argparse
import copy
import hashlib
import json
from pathlib import Path
import shutil

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "evaluator"))
from evaluate import run_episode, aggregate


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--tape", type=int, choices=(1, 2), required=True)
    parser.add_argument("--policy", choices=("adaptive", "robust", "static", "uniform"), default="adaptive")
    arguments = parser.parse_args()
    episodes = json.loads((ROOT / "evaluator/hidden/episodes.json").read_text())["episodes"]
    results = []
    manifest = []
    for index, original in enumerate(episodes):
        episode = copy.deepcopy(original)
        episode["sample_seed"] = int(np.random.SeedSequence([97216183, arguments.tape, index]).generate_state(1, dtype=np.uint64)[0])
        replay_name = str(arguments.tape) if arguments.policy == "adaptive" else arguments.policy + "_" + str(arguments.tape)
        leaf = ROOT / "adversary/replays" / replay_name / episode["id"] / "submission"
        leaf.mkdir(parents=True, exist_ok=False)
        for name in ("solution.py", "local_model.py"):
            shutil.copyfile(ROOT / "adversary/portfolio" / name, leaf / name)
        manifest.append({"episode": episode["id"], "supplementary_sample_seed": episode["sample_seed"],
                         "source_sha256": hashlib.sha256((leaf / "solution.py").read_bytes()).hexdigest()})
        result = run_episode(episode, leaf, ["/usr/bin/python3", "/submission/solution.py", "--policy", arguments.policy])
        results.append(result)
        report = aggregate(results)
        report.update({"official_suite": False, "supplementary_only": True, "noise_tape": arguments.tape,
                       "parameter_fixtures_unchanged": True, "manifest": manifest})
        (ROOT / "adversary/validation" / ("replay_" + replay_name + ".json")).write_text(json.dumps(report, indent=2) + "\n")
        print(json.dumps(result), flush=True)


if __name__ == "__main__":
    main()
