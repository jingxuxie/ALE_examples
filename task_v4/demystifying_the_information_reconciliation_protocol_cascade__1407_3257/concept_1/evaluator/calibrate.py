import copy
import json
import subprocess
import sys
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "participant"))
from baseline import baseline_policy
from cascade_sim import run_frame
from scoring import evaluate_suite


def save(relative, data):
    text = json.dumps(data, indent=2, allow_nan=False) + "\n"
    patch = f"*** Begin Patch\n*** Add File: {ROOT / relative}\n" + "".join("+" + line + "\n" for line in text.splitlines()) + "*** End Patch\n"
    subprocess.run(["apply_patch"], input=patch, text=True, check=True, capture_output=True)


def main():
    suite = json.loads((ROOT / "participant/inputs/train.json").read_text())
    baseline = baseline_policy()
    references = {str(seed): run_frame(case, seed, baseline) for case in suite["cases"] for seed in case["frame_seeds"]}
    variants = {"baseline": baseline}
    for passes in [6, 8, 10, 12]:
        policy = copy.deepcopy(baseline)
        policy["max_passes"] = passes
        variants[f"passes_{passes}"] = policy
    for scale in [0.5, 2]:
        for stage in [0, 1]:
            policy = copy.deepcopy(baseline)
            policy["schedule"][stage]["size"]["scale"] = scale
            variants[f"stage_{stage}_scale_{scale}"] = policy
    policy = copy.deepcopy(baseline)
    for action in policy["schedule"]:
        action["batch"] = "smallest"
    variants["smallest_batch"] = policy
    policy = copy.deepcopy(baseline)
    policy["schedule"][1]["size"] = {"basis": "parity", "scale": 4, "round": "nearest"}
    variants["parity_second"] = policy
    results = []
    for name, policy in variants.items():
        started = time.monotonic()
        result = evaluate_suite(policy, suite, references)
        save(f"adversary/calibration/{name}.json", result)
        save(f"adversary/calibration/{name}.policy.json", policy)
        summary = {"name": name, "improvement": result["improvement"],
                   "family_improvements": {family: 1 - values["ratio"] for family, values in result["families"].items()},
                   "fer": result["candidate_total"]["fer"], "stress_fer": result["stress"]["fer"],
                   "seconds": time.monotonic() - started}
        results.append(summary)
        print(json.dumps(summary), flush=True)
    save("adversary/calibration/summary.json", results)


if __name__ == "__main__":
    main()
