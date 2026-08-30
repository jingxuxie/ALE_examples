import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path

from search import ROOT, FastRouter, evaluate_witness, validate


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("candidate", type=Path)
    parser.add_argument("--output", default="verification")
    parser.add_argument("--submit", action="store_true")
    arguments = parser.parse_args()
    witness = json.loads(arguments.candidate.read_text())
    count, edges, gates, reference = validate(witness)
    fast = FastRouter(witness["hardware"])
    predicted = fast.evaluate(gates, list(range(108)))
    result = evaluate_witness(witness)
    actual = [setting["swaps"] for family in result["families"] for setting in family["settings"]]
    if predicted != actual:
        raise RuntimeError(f"fast model mismatch: {[(index, left, right) for index, (left, right) in enumerate(zip(predicted, actual)) if left != right]}")
    coverage = Counter(node for gate in gates for node in gate)
    pairs = Counter(tuple(sorted(gate)) for gate in gates)
    partners = [set() for node in range(16)]
    for left, right in gates:
        partners[left].add(right)
        partners[right].add(left)
    details = {
        "witness_sha256": hashlib.sha256((json.dumps(witness, indent=2) + "\n").encode()).hexdigest(),
        "hardware": witness["hardware"],
        "wire_gate_counts": [coverage[node] for node in range(16)],
        "wire_distinct_partners": [len(adjacent) for adjacent in partners],
        "distinct_pairs": len(pairs),
        "max_pair_occurrences": max(pairs.values()),
        "all_fast_counts_match_public_checker": True,
        "public_checker": result,
    }
    (ROOT / (arguments.output + ".json")).write_text(json.dumps(details, indent=2) + "\n")
    print("candidate", arguments.candidate, "valid", result["valid"], "passed", result["passed"],
          "reference", reference, "gates", len(gates), flush=True)
    for family in result["families"]:
        print(family["name"], "swaps", family["portfolio_swaps"], "swap_ratio", family["swap_ratio"],
              "native_ratio", family["native_ratio"], "gap", family["swap_gap"], flush=True)
    print("coverage", details["wire_gate_counts"], "partners", details["wire_distinct_partners"],
          "pairs", len(pairs), "max_pair_occurrences", max(pairs.values()), flush=True)
    if arguments.submit:
        if not result["passed"]:
            raise RuntimeError("refusing to submit a nonpassing witness")
        output = ROOT / "witness.json"
        output.write_text(json.dumps(witness, indent=2) + "\n")
        print("submitted", output, "sha256", hashlib.sha256(output.read_bytes()).hexdigest(), flush=True)


if __name__ == "__main__":
    main()
