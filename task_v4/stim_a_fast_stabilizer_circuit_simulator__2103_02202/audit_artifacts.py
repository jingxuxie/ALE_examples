import importlib.util
import json
from pathlib import Path
import sys

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parent


def module(path, name):
    specification = importlib.util.spec_from_file_location(name, path)
    loaded = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(loaded)
    return loaded


def main():
    counterexample = ROOT / "concept_2"
    evaluator = module(counterexample / "evaluator/evaluate.py", "counterexample_evaluator")
    workspace = counterexample / "adversary/parser_audit"
    workspace.mkdir(exist_ok=True)
    cases = {"duplicates": b'{"faults":[],"faults":[]}', "nan": b'{"faults":[NaN]}',
             "too_big": b" " * 20000, "deep": b"[" * 3000 + b"]" * 3000,
             "boolean": b'{"faults":[true]}', "trailing": b'{"faults":[]} ignored'}
    results = {}
    for name, content in cases.items():
        path = workspace / (name + ".json")
        path.write_bytes(content)
        result = evaluator.evaluate_path(path)
        if result["valid"] or result["reason"].startswith("input_error"):
            raise RuntimeError("malformed artifact test failed: " + name)
        results[name] = result
    link = workspace / "link.json"
    if not link.exists():
        link.symlink_to(counterexample / "evaluator/hidden/witness/witness.json")
    result = evaluator.evaluate_path(link)
    if result["valid"]:
        raise RuntimeError("symlink witness accepted")
    results["symlink"] = result
    original = json.loads((counterexample / "evaluator/hidden/witness/witness.json").read_text())
    reordered = workspace / "reordered.json"
    reordered.write_text(json.dumps({"faults": list(reversed(original["faults"]))}))
    result = evaluator.evaluate_path(reordered)
    if not result["passed"]:
        raise RuntimeError("valid reordered witness rejected")
    results["reordered_witness"] = result
    (counterexample / "adversary/parser_audit.json").write_text(json.dumps({"passed": True, "cases": results}, indent=2) + "\n")
    design = ROOT / "concept_3"
    sys.path.insert(0, str(design / "evaluator"))
    evaluator = module(design / "evaluator/evaluate.py", "design_evaluator")
    alternative = design / "adversary/equivalent_witness"
    alternative.mkdir(exist_ok=True)
    circuit = json.loads((design / "evaluator/hidden/witness/circuit.json").read_text())
    circuit["layers"].extend([[{"gate": "H", "targets": [0]}], [{"gate": "H", "targets": [0]}]])
    (alternative / "circuit.json").write_text(json.dumps(circuit))
    result = evaluator.evaluate(alternative)
    if not result["passed"]:
        raise RuntimeError("valid noncanonical circuit rejected")
    (design / "adversary/noncanonical_acceptance.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"passed": True, "counterexample_parser_cases": len(results), "noncanonical_circuit_score": result["score"]}))


if __name__ == "__main__":
    main()
