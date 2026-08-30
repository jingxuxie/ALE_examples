import json
from pathlib import Path
import secrets
import sys

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "participant" / "input"))

from simulator import FAMILIES, parameter_dict, sample_prior


def main():
    hidden = ROOT / "evaluator" / "hidden" / "episodes.json"
    if hidden.exists():
        raise SystemExit("Refusing to replace an existing fixed hidden suite")
    episodes = []
    for family in FAMILIES:
        for index in range(6):
            parameter_seed = secrets.randbits(128)
            theta = sample_prior(family, np.random.default_rng(parameter_seed))
            episodes.append({"id": secrets.token_hex(6), "family": family,
                             "parameter_seed": parameter_seed, "outcome_seed": secrets.randbits(128),
                             "parameters": parameter_dict(theta)})
    np.random.default_rng(secrets.randbits(128)).shuffle(episodes)
    hidden.write_text(json.dumps({"episodes": episodes}, indent=2) + "\n")
    public_episodes = []
    for index, family in enumerate(FAMILIES):
        theta = sample_prior(family, np.random.default_rng(1100 + index))
        public_episodes.append({"id": "public-" + str(index + 1), "family": family,
                                "outcome_seed": 2200 + index, "parameters": parameter_dict(theta)})
    (ROOT / "participant" / "input" / "public_examples.json").write_text(json.dumps({"episodes": public_episodes}, indent=2) + "\n")


if __name__ == "__main__":
    main()
