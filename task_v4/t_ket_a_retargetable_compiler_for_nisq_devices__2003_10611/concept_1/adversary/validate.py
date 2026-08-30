import copy
import importlib.util
import json
from pathlib import Path
import random
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "participant" / "workspace"))
sys.path.insert(0, str(ROOT / "participant" / "baseline"))
sys.path.insert(0, str(ROOT.parent / "authoring"))
from routing import validate
from solve import solve
from sandbox import run_python


def algebra_check(case, route):
    count = case["n"]
    logical_rows = [1 << index for index in range(count)]
    for first, second in case["gates"]:
        logical_rows[second] ^= logical_rows[first]
    physical_rows = [0] * count
    positions = case["initial"][:]
    occupants = [0] * count
    for logical, physical in enumerate(positions):
        physical_rows[physical] = 1 << logical
        occupants[physical] = logical
    for operation in route["operations"]:
        if operation[0] == "swap":
            first, second = operation[1:]
            physical_rows[second] ^= physical_rows[first]
            physical_rows[first] ^= physical_rows[second]
            physical_rows[second] ^= physical_rows[first]
            occupants[first], occupants[second] = occupants[second], occupants[first]
            positions[occupants[first]] = first
            positions[occupants[second]] = second
        else:
            first, second = case["gates"][operation[1]]
            physical_rows[positions[second]] ^= physical_rows[positions[first]]
    assert [physical_rows[positions[logical]] for logical in range(count)] == logical_rows


def main():
    generator = random.Random(57191)
    trials = []
    for number in range(32):
        count = generator.randrange(4, 10)
        edges = [[index, index + 1, generator.uniform(0.5, 2.0)] for index in range(count - 1)]
        positions = list(range(count))
        generator.shuffle(positions)
        case = {"n": count, "edges": edges, "gates": [generator.sample(range(count), 2) for _ in range(30)], "initial": positions}
        answer = solve(case)
        metrics = validate(case, answer)
        algebra_check(case, answer)
        trials.append(metrics)
        malformed = [None, {}, {"operations": answer["operations"][:-1]},
                     {"operations": [["gate", -1]]}, {"operations": [["swap", 0, count - 1]]},
                     {"operations": [["gate", True]]}, {"operations": answer["operations"] + [["gate", 0]]}]
        for candidate in malformed:
            try:
                validate(case, candidate)
            except (ValueError, TypeError, KeyError, IndexError):
                continue
            raise AssertionError("malformed route accepted")
    probe = run_python(ROOT.parent / "authoring" / "sandbox_probe", "solve.py",
                       {"forbidden": {"hidden": str(ROOT / "evaluator" / "hidden" / "cases.json"),
                                      "parent": str(ROOT.parent / "authoring" / "sources.md"),
                                      "proc": "/proc/self/environ"}}, 8)
    assert probe["returncode"] == 0, probe
    probe_result = json.loads(probe["stdout"])
    assert all(probe_result[label] == "denied" for label in ("hidden", "parent", "proc", "network")), probe_result
    assert probe_result["scratch_write"] == "ok"
    assert probe_result["submission_cwd"]
    assert probe_result["one_cpu"] and probe_result["affinity_lock"] == "denied"
    result = {"valid": True, "random_replay_and_independent_GF2_cases": len(trials),
              "malformed_cases_rejected": 32 * 7, "sandbox": probe_result}
    (ROOT / "evaluator" / "hidden" / "validation.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
