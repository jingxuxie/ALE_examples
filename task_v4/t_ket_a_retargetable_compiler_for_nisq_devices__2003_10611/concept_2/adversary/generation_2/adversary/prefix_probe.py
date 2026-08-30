import collections
import copy
import json
import math
from pathlib import Path
import random
import sys


ROOT = Path(__file__).resolve().parents[1]
CONCEPT = ROOT.parents[1]
sys.path.insert(0, str(ROOT / "participant" / "input"))
from benchmark import evaluate_witness
from router import hardware
from validation import validate


def prepend(original, length, seed):
    generator = random.Random(seed)
    count, edges = hardware(original["hardware"])
    pair_counts = collections.Counter(tuple(sorted(pair)) for pair in original["gates"])
    occurrences = collections.Counter(wire for pair in original["gates"] for wire in pair)
    maximum = min(40, math.ceil(4 * (len(original["gates"]) + length) / count))
    prefix = []
    last = [None] * count
    for _ in range(length):
        possible = [edge for edge in edges if pair_counts[edge] < 8
                    and all(occurrences[wire] < maximum for wire in edge)
                    and not all(last[wire] == edge for wire in edge)]
        if not possible:
            return None
        edge = generator.choice(possible)
        pair_counts[edge] += 1
        for wire in edge:
            occurrences[wire] += 1
            last[wire] = edge
        pair = list(edge)
        if generator.randrange(2):
            pair.reverse()
        prefix.append(pair)
    witness = copy.deepcopy(original)
    witness["gates"] = prefix + original["gates"]
    witness["route"] = [["gate", index, first, second] for index, (first, second) in enumerate(prefix)]
    for operation in original["route"]:
        if operation[0] == "gate":
            witness["route"].append(["gate", operation[1] + length, operation[2], operation[3]])
        else:
            witness["route"].append(operation[:])
    try:
        validate(witness)
    except ValueError:
        return None
    return witness


def main():
    original = json.loads((CONCEPT / "attempts" / "v_1.frozen" / "witness.json").read_text())
    destination = ROOT / "adversary" / "prefix_probe"
    destination.mkdir(exist_ok=True)
    records = []
    for length in (32, 40, 48, 64):
        for seed in range(88103, 88203):
            witness = prepend(original, length, seed)
            if witness is None:
                continue
            result = evaluate_witness(witness)
            record = {"prefix_gates": length, "seed": seed, "valid": result["valid"],
                      "passed": result["passed"], "core_score": result["core_score"],
                      "worst_family_score": result["worst_family_score"],
                      "portfolio_swaps": [family["portfolio_swaps"] for family in result["families"]]}
            records.append(record)
            print(json.dumps(record), flush=True)
            (destination / f"candidate_{length}.json").write_text(json.dumps(witness, separators=(",", ":")) + "\n")
            (destination / f"score_{length}.json").write_text(json.dumps(result, indent=2) + "\n")
            break
    summary = {"generation": 2, "method": "legal native prologues composed with the private first champion",
               "thresholds_unchanged": True, "records": records,
               "passing_witness_known": any(record["passed"] for record in records)}
    (destination / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")


if __name__ == "__main__":
    main()
