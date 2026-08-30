import argparse
import json
from pathlib import Path
import random
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "workspace"))
from replay import replay


def solve(deployment, trials):
    generator = random.Random(760142)
    best_errors = []
    best_rank = (-1, -1)
    for trial in range(trials):
        errors = sorted(generator.sample(range(deployment["n"]), 24))
        result = replay(deployment, errors)
        rank = (len(result["residual"]), result["initial_odd"])
        if rank > best_rank:
            best_errors, best_rank = errors, rank
    return {"errors": best_errors}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--trials", type=int, default=32)
    arguments = parser.parse_args()
    artifact = solve(json.loads(Path(arguments.input).read_text()), arguments.trials)
    Path(arguments.output).write_text(json.dumps(artifact) + "\n")
