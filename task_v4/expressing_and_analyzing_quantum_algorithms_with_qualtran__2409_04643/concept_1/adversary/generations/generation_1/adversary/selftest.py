import importlib.util
import itertools
import json
import random
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "participant" / "workspace"))
from model import baseline_order, metrics

spec = importlib.util.spec_from_file_location("private_evaluator", ROOT / "evaluator" / "evaluate.py")
judge = importlib.util.module_from_spec(spec)
spec.loader.exec_module(judge)


def main():
    checks = 0
    rng = random.Random(9017)
    for size in range(2, 7):
        for _ in range(8):
            edges = [[source, destination, rng.randrange(1, 9)]
                     for source in range(size) for destination in range(source + 1, size)
                     if rng.random() < 0.4]
            if not edges:
                edges = [[0, size - 1, 3]]
            case = {"nodes": [{"workspace": rng.randrange(1, 8), "duration": rng.randrange(1, 9)} for _ in range(size)], "edges": edges}
            for order in itertools.permutations(range(size)):
                try:
                    public = metrics(case, list(order))
                except ValueError:
                    try:
                        judge.simulate(case, list(order))
                    except ValueError:
                        checks += 1
                        continue
                    raise AssertionError("invalid dependency accepted")
                assert public == judge.simulate(case, list(order))
                checks += 1
    tiny = {"nodes": [{"duration": 1, "workspace": 0}, {"duration": 1, "workspace": 0}], "edges": [[0, 1, 5]]}
    assert judge.simulate(tiny, [0, 1]) == {"peak": 5, "qubit_time": 10}
    for bad in ([0, 0], [True, 0], [0.0, 1], [1, 0], [-1, 0], [0]):
        try:
            judge.simulate(tiny, bad)
        except ValueError:
            checks += 1
        else:
            raise AssertionError("bad schedule accepted")
    for text in ('{"a":1,"a":2}', '{"a":NaN}', '{"a":Infinity}'):
        try:
            json.loads(text, object_pairs_hook=judge.unique_pairs, parse_constant=judge.reject_constant)
        except ValueError:
            checks += 1
        else:
            raise AssertionError("bad JSON accepted")
    bank = json.loads((ROOT / "participant" / "input" / "workloads.json").read_text())
    private = json.loads((ROOT / "evaluator" / "hidden" / "workloads.json").read_text())
    assert bank == private
    baseline_metrics = json.loads((ROOT / "evaluator" / "hidden" / "baseline_metrics.json").read_text())
    for case in bank["cases"]:
        assert judge.simulate(case, baseline_order(case)) == baseline_metrics[case["id"]]
        checks += 1
    witness = judge.evaluate(ROOT / "adversary" / "portfolio_witness")
    assert witness["passed"] and witness["valid"]
    result = {"passed": True, "checks": checks, "private_witness_core": witness["core_score"], "private_witness_worst": witness["worst_family_score"]}
    (ROOT / "adversary" / "selftest.json").write_text(json.dumps(result, indent=2))
    print(json.dumps(result))


if __name__ == "__main__":
    main()
