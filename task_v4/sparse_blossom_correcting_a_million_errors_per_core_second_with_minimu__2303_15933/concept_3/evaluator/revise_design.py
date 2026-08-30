import hashlib
import json
from pathlib import Path

import numpy as np

from hidden.simulator import add_gain_ladder


ROOT = Path(__file__).resolve().parents[1]


def main():
    for relative in ("evaluator/hidden/episodes.json", "participant/input/training.json"):
        path = ROOT / relative
        content = json.loads(path.read_text())
        for episode in content["episodes"]:
            for index, channel in enumerate(episode["spec"]["channels"]):
                if channel["family"] == "rare":
                    quantile = np.log(episode["rates"][index] / 0.0004) / np.log(0.006 / 0.0004)
                    episode["rates"][index] = float(0.00005 * (0.015 / 0.00005)**quantile)
            add_gain_ladder(episode["spec"])
        path.write_text(json.dumps(content, indent=2) + "\n")
    targets_path = ROOT / "evaluator/hidden/targets.json"
    (ROOT / "participant/input/targets.json").write_bytes(targets_path.read_bytes())
    manifest = {"episodes_sha256": hashlib.sha256((ROOT / "evaluator/hidden/episodes.json").read_bytes()).hexdigest(),
                "targets_sha256": hashlib.sha256(targets_path.read_bytes()).hexdigest(),
                "private_episodes": 12, "training_episodes": 6,
                "revision": "v2 gain ladder, deterministic quantile mapping of all original rare rates, no episode filtering or seed replacement"}
    (ROOT / "evaluator/hidden/freeze.json").write_text(json.dumps(manifest, indent=2) + "\n")


if __name__ == "__main__":
    main()
