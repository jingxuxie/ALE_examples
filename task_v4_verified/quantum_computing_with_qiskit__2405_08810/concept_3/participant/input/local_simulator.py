import argparse
import json
import sys
from pathlib import Path

import numpy as np

from model import CONFIG, draw_parameters
from runtime import aggregate, run_episode


def main():
    parser = argparse.ArgumentParser(description="Public, trusted-code development harness; not an isolation boundary")
    parser.add_argument("submission", type=Path)
    parser.add_argument("--seed", type=int, default=7241)
    parser.add_argument("--episodes", type=int, default=4)
    parser.add_argument("--family", choices=CONFIG["suite"]["families"])
    parser.add_argument("--output", type=Path)
    arguments = parser.parse_args()
    if not 1 <= arguments.episodes <= 128:
        parser.error("episodes must be in [1,128]")
    submission = arguments.submission.resolve()
    script = submission if submission.is_file() else submission / "solution.py"
    seeds = np.random.SeedSequence(arguments.seed).spawn(2 * arguments.episodes)
    results = []
    for episode_index in range(arguments.episodes):
        family = arguments.family or CONFIG["suite"]["families"][episode_index % 4]
        parameters = draw_parameters(np.random.default_rng(seeds[2 * episode_index]), family)
        measurement_seed = int(seeds[2 * episode_index + 1].generate_state(1, dtype=np.uint64)[0])
        result = run_episode([sys.executable, "-u", str(script)], parameters, measurement_seed, cwd=script.parent)
        result.update({"family": family, "true_parameters": parameters.tolist()})
        results.append(result)
        print(json.dumps({"episode": episode_index, **result}), file=sys.stderr, flush=True)
    report = {**aggregate(results), "development_only": True, "seed": arguments.seed, "episodes": results}
    encoded = json.dumps(report, indent=2, allow_nan=False) + "\n"
    if arguments.output:
        arguments.output.write_text(encoded)
    print(encoded)


if __name__ == "__main__":
    main()
