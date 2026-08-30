import argparse
import hashlib
import json
from pathlib import Path
import random
import sys
import time

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "participant/workspace"))
from channel import fit_table, marginals
sys.path.insert(0, str(ROOT / "participant/baseline"))
from solve import solve as baseline_solve
sys.path.insert(0, str(ROOT / "evaluator"))
from exact import score_answer


def optimize(model, seconds, seed):
    generator = random.Random(seed)
    started = time.monotonic()
    initial = baseline_solve(model)
    cache = {}

    def assess(selection):
        key = tuple(sorted(selection))
        if key not in cache:
            distribution = marginals(model, key)
            table, risks = fit_table(distribution)
            cache[key] = (max(risks), table)
        return cache[key]

    best_selection = tuple(initial["selected"])
    best_risk, best_table = assess(best_selection)
    current = best_selection
    current_risk = best_risk
    iteration = 0
    restart = 0
    while time.monotonic() - started < seconds:
        iteration += 1
        if iteration % 400 == 0:
            restart += 1
            current = tuple(sorted(generator.sample(range(len(model["taps"])), model["budget"])))
            current_risk = assess(current)[0]
        proposal = list(current)
        swaps = 2 if generator.random() < 0.2 else 1
        for position in generator.sample(range(len(proposal)), swaps):
            proposal[position] = generator.choice([index for index in range(len(model["taps"])) if index not in proposal])
        proposal = tuple(sorted(proposal))
        proposal_risk, proposal_table = assess(proposal)
        temperature = 0.0005 + 0.015 * (1 - (iteration % 400) / 400) ** 3
        if proposal_risk < current_risk or generator.random() < np.exp(min(0, (current_risk - proposal_risk) / temperature)):
            current, current_risk = proposal, proposal_risk
        if proposal_risk < best_risk:
            best_selection, best_risk, best_table = proposal, proposal_risk, proposal_table
    answer = {"selected": list(best_selection), "correction": best_table}
    return answer, {"iterations": iteration, "distinct_subsets": len(cache), "restarts": restart,
                    "elapsed_seconds": time.monotonic() - started, **score_answer(model, answer)}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--seconds", type=float, default=120)
    parser.add_argument("--family")
    arguments = parser.parse_args()
    records = []
    for index, path in enumerate(sorted((ROOT / "evaluator/hidden/instances").glob("*.json"))):
        if arguments.family and not path.name.startswith(arguments.family):
            continue
        model = json.loads(path.read_text())
        answer, scores = optimize(model, arguments.seconds, 952057 + 371 * index)
        destination = ROOT / "adversary/portfolio_answers" / path.name
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(json.dumps(answer) + "\n")
        record = {"instance": path.stem, "input_sha256": hashlib.sha256(path.read_bytes()).hexdigest(), **scores}
        records.append(record)
        print(json.dumps(record), flush=True)
    destination = ROOT / "adversary" / ("portfolio_" + (arguments.family or "all") + ".json")
    destination.write_text(json.dumps(records, indent=2) + "\n")


if __name__ == "__main__":
    main()
