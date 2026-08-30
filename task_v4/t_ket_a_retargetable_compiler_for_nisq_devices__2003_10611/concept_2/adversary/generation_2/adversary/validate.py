import datetime
import hashlib
import json
from pathlib import Path
import random
import sys
import time


ROOT = Path(__file__).resolve().parents[1]
CONCEPT = ROOT.parents[1]
sys.path.insert(0, str(ROOT / "participant" / "input"))
from benchmark import evaluate_file
from router import hardware, relabelings, route, settings, transform
from validation import replay


def main():
    generator = random.Random(661027)
    checks = []
    for graph in ("ring16", "ladder16", "grid16"):
        count, edges = hardware(graph)
        for number in range(3):
            gates = [list(generator.choice(edges)) for _ in range(72)]
            if number:
                label = list(range(count))
                generator.shuffle(label)
                gates = [[label[first], label[second]] for first, second in gates]
            for name, logical, physical in relabelings(count):
                renamed, mapped_edges, initial = transform(gates, edges, logical, physical)
                result = route(renamed, count, mapped_edges, initial, settings()[-1])
                measured = replay(renamed, count, mapped_edges, result["route"], result["final_mapping"], initial)
                assert measured["swaps"] == result["swaps"]
                checks.append({"graph": graph, "case": number, "family": name, **measured})
    baseline = evaluate_file(ROOT / "participant" / "baseline" / "witness.json")
    champion = evaluate_file(CONCEPT / "attempts" / "v_1.frozen" / "witness.json")
    assert baseline["valid"] and not baseline["passed"]
    assert champion["valid"] and not champion["passed"]
    legacy = CONCEPT / "participant" / "input" / "validation.py"
    assert legacy.read_bytes() == (ROOT / "participant" / "input" / "validation.py").read_bytes()
    result = {"passed": True, "new_policy_exact_replays": len(checks), "checks": checks,
              "legacy_parser_source_identical": True, "inherited_parser_validation": "concept_2/adversary/validation.json",
              "baseline": baseline, "generation_1_champion": champion,
              "settings": len(settings()), "relabelings": len(relabelings(16))}
    hidden = ROOT / "evaluator" / "hidden"
    (hidden / "validation.json").write_text(json.dumps(result, indent=2) + "\n")
    (hidden / "baseline_score.json").write_text(json.dumps(baseline, indent=2) + "\n")
    (hidden / "old_champion_score.json").write_text(json.dumps(champion, indent=2) + "\n")
    frozen = {"generation": 2, "frozen_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
              "target": {"swap_ratio": 2.5, "native_ratio": 1.35, "swap_gap": 16},
              "settings": 25, "relabelings": 6,
              "participant_hashes": {str(path.relative_to(ROOT / "participant")): hashlib.sha256(path.read_bytes()).hexdigest()
                                     for path in sorted((ROOT / "participant").rglob("*"))
                                     if path.is_file() and "__pycache__" not in path.parts}}
    (hidden / "freeze.json").write_text(json.dumps(frozen, indent=2) + "\n")
    print(json.dumps({"passed": True, "new_policy_replays": len(checks),
                      "baseline_core": baseline["core_score"], "old_champion_core": champion["core_score"],
                      "old_champion_worst": champion["worst_family_score"],
                      "old_champion_swaps": [family["portfolio_swaps"] for family in champion["families"]]}, indent=2))


if __name__ == "__main__":
    main()
