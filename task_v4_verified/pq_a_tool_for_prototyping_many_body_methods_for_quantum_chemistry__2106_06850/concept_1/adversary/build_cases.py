import ast
import hashlib
import importlib.util
import json
import math
import random
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT.parent / "authoring/sources/pdaggerq"
sys.path.insert(0, str(ROOT / "participant/workspace"))
sys.path.insert(0, str(ROOT / "participant/baseline"))
from contract import validate, term_key
from solve import term_frontier, solve


def extract(filename):
    module = ast.parse(filename.read_text())
    records = []
    seen = set()
    for function in module.body:
        if not isinstance(function, ast.FunctionDef):
            continue
        for node in ast.walk(function):
            if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Name) or node.func.id != "einsum":
                continue
            try:
                expression = ast.literal_eval(node.args[0])
                if "->" not in expression:
                    continue
                lhs, output = expression.split("->")
                axes = lhs.split(",")
                if not 3 <= len(axes) <= 6 or len(output) > 6:
                    continue
                tensors = {}
                inputs = []
                for operand, indices in zip(node.args[1:], axes):
                    base = operand.value.id if isinstance(operand, ast.Subscript) else operand.id
                    if base not in {"f", "g", "t1", "t2", "t3", "t4", "l1", "l2", "r1", "r2", "r3"}:
                        raise ValueError("not a primitive input")
                    kinds = ["o" if label in "ijklmn" else "v" for label in indices]
                    if any(label not in "abcdefghijklmn" for label in indices) or len(set(indices)) != len(indices):
                        raise ValueError("unsupported labels")
                    name = base + "_" + "".join(kinds)
                    tensors[name] = kinds
                    inputs.append([name, indices])
                if len(inputs) != len(axes):
                    continue
                counts = Counter("".join(axes))
                if set(label for label, count in counts.items() if count == 1) != set(output) or any(count > 2 for count in counts.values()):
                    continue
                term = {"inputs": inputs, "output": output}
                key = term_key(term)
                if key in seen:
                    continue
                seen.add(key)
                records.append({"term": term, "tensors": tensors, "function": function.name,
                                "line": node.lineno, "file": str(filename.relative_to(SOURCE))})
            except (AttributeError, ValueError, TypeError, SyntaxError):
                continue
    return records


def make_case(records, rng, occupied, virtual, number, cap_factor):
    selected = rng.sample(records, min(number, len(records)))
    tensors = {}
    terms = []
    for record in selected:
        tensors.update(record["tensors"])
        terms.append(record["term"])
    rng.shuffle(terms)
    case = {"dimensions": {"o": occupied, "v": virtual}, "tensors": tensors,
            "index_types": {label: "o" if label in "ijklmn" else "v" for label in "abcdefghijklmn"},
            "terms": terms, "memory_cap": 10**30}
    records = [term_frontier(case, term)[0] for term in terms]
    optimal_peak = max(record[1] for record in records)
    case["memory_cap"] = max(1, math.ceil(optimal_peak * cap_factor))
    metric = validate(case, solve(case))
    return case, metric


def main():
    rng = random.Random(821660685092)
    families = {}
    family_sources = {
        "right_triples": ["examples/full_cc_codes/ccsdt.py"],
        "left_density": ["examples/full_cc_codes/lambda_ccsd.py"],
        "linear_response": ["examples/full_cc_codes/eom_ccsd.py"],
        "quadruples": ["examples/full_cc_codes/ccsdtq.py"],
    }
    for family, paths in family_sources.items():
        records = sum((extract(SOURCE / path) for path in paths), [])
        if len(records) < 8:
            raise ValueError((family, len(records)))
        families[family] = records
        print(family, len(records), flush=True)
    provenance = {family: records for family, records in families.items()}
    (ROOT / "evaluator/hidden/source_terms.json").write_text(json.dumps(provenance, indent=2))
    entries = []
    for family, records in families.items():
        for index, (occupied, virtual, number, cap) in enumerate([
                (4, 12, 32, 1.10), (8, 32, 48, 1.10), (12, 72, 64, 1.15),
                (20, 40, 64, 1.10), (6, 90, 72, 1.20), (16, 112, 80, 1.15)]):
            case, metric = make_case(records, rng, occupied, virtual, number, cap)
            name = family + "_" + str(index) + ".json"
            (ROOT / "evaluator/hidden" / name).write_text(json.dumps(case, sort_keys=True))
            entries.append({"file": name, "family": family, "baseline": metric})
        public, metric = make_case(records, random.Random(107 + len(records)), 5, 15, 20, 1.20)
        (ROOT / "participant/input" / (family + ".json")).write_text(json.dumps(public, indent=2))
        (ROOT / "participant/input" / (family + ".baseline.json")).write_text(json.dumps(metric, indent=2))
    manifest = {"mode": "A", "target_geomean_speedup": 1.75, "target_worst_family_speedup": 1.15,
                "require_all_valid": True, "planner_timeout_seconds": 30,
                "planner_memory_bytes": 2147483648, "cases": entries}
    (ROOT / "evaluator/hidden/manifest.json").write_text(json.dumps(manifest, indent=2))
    score = {"core_score": 1.0, "worst_family_score": 1.0, "passed": False,
             "valid": True, "reason": "Exact per-term Pareto-optimal baseline, without cross-term reuse",
             "cases": entries}
    (ROOT / "adversary/baseline_score.json").write_text(json.dumps(score, indent=2))


if __name__ == "__main__":
    main()
