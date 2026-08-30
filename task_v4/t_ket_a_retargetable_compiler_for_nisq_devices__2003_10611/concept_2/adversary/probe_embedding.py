import json
from pathlib import Path
import random
import sys
import time


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "participant" / "input"))
from router import graph_data, hardware, relabelings, transform
from validation import replay
from embedding_repair import suffix_route, token_plan


def main():
    generator = random.Random(41071)
    token_checks = 0
    for graph in ("ring16", "grid16", "ladder16"):
        count, edges = hardware(graph)
        neighbors, distances = graph_data(count, edges)
        for _ in range(8):
            target = list(range(count))
            generator.shuffle(target)
            plan = token_plan(list(range(count)), target, neighbors, distances, edges, budget=100)
            occupants = list(range(count))
            positions = list(range(count))
            for first, second in plan:
                assert tuple(sorted((first, second))) in edges
                occupants[first], occupants[second] = occupants[second], occupants[first]
                positions[occupants[first]] = first
                positions[occupants[second]] = second
            assert positions == target
            token_checks += 1
    witness = json.loads((ROOT / "attempts" / "v_1.frozen" / "witness.json").read_text())
    count, edges = hardware(witness["hardware"])
    records = []
    for name, logical, physical in relabelings(count):
        gates, mapped_edges, initial = transform(witness["gates"], edges, logical, physical)
        started = time.monotonic()
        result = suffix_route(gates, count, mapped_edges, initial)
        metrics = replay(gates, count, mapped_edges, result["route"], result["final_mapping"], initial)
        records.append({"family": name, "seconds": time.monotonic() - started,
                        "embedding_cutoff": result.get("embedding_cutoff"), **metrics})
    output = {"token_replay_checks": token_checks, "champion": records,
              "general_policy": "suffix interaction embedding plus explicit paid native token routing",
              "original_champion_swaps": 8, "original_portfolio_minimum": 66}
    (ROOT / "adversary" / "embedding_probe.json").write_text(json.dumps(output, indent=2) + "\n")
    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
