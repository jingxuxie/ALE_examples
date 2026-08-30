import argparse
import hashlib
import json
import secrets
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "participant" / "input"))
from model import CONFIG, draw_parameters


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", type=int)
    arguments = parser.parse_args()
    destination = ROOT / "evaluator" / "hidden" / "episodes.json"
    if destination.exists():
        raise SystemExit("Refusing to overwrite a frozen suite")
    master_seed = arguments.seed if arguments.seed is not None else secrets.randbits(128)
    seeds = np.random.SeedSequence(master_seed).spawn(65)
    episodes = []
    for episode_index in range(32):
        family = CONFIG["suite"]["families"][episode_index % 4]
        parameters = draw_parameters(np.random.default_rng(seeds[2 * episode_index]), family)
        measurement_seed = int(seeds[2 * episode_index + 1].generate_state(1, dtype=np.uint64)[0])
        episodes.append({"family": family, "parameters": parameters.tolist(), "measurement_seed": measurement_seed})
    np.random.default_rng(seeds[-1]).shuffle(episodes)
    payload = {"version": 1, "master_seed": master_seed, "episodes": episodes}
    encoded = json.dumps(payload, indent=2, allow_nan=False) + "\n"
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(encoded)
    manifest = {"generated_utc": datetime.now(timezone.utc).isoformat(), "episodes_sha256": hashlib.sha256(encoded.encode()).hexdigest(),
                "episode_count": 32, "family_counts": {family: 8 for family in CONFIG["suite"]["families"]},
                "parameter_and_measurement_streams": "separate SeedSequence children; independent public development seeds"}
    destination.with_name("manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
