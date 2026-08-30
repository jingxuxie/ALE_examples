import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import tempfile


ROOT = Path(__file__).resolve().parents[1]


def module_at(name, relative):
    specification = importlib.util.spec_from_file_location(name, ROOT / relative)
    module = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(module)
    return module


def independent_replay(case, gates):
    matrix = [[int(row == column) for column in range(case["n"])] for row in range(case["n"])]
    seen = {tuple(row) for row in matrix}
    for control, target in gates:
        matrix[target] = [(left + right) % 2 for left, right in zip(matrix[target], matrix[control])]
        seen.add(tuple(matrix[target]))
    target = [[(mask >> column) & 1 for column in range(case["n"])] for mask in case["target_rows"]]
    assert matrix == target
    for mask in case["required_parities"]:
        assert tuple((mask >> column) & 1 for column in range(case["n"])) in seen


def main():
    evaluator = module_at("native_evaluator", "evaluator/evaluate.py")
    baseline = module_at("native_baseline", "participant/baseline/synthesize.py")
    suite = evaluator.load_suite()
    public_bytes = (ROOT / "participant/input/instances.json").read_bytes()
    frozen_bytes = (ROOT / "evaluator/hidden/frozen_instances.json").read_bytes()
    assert public_bytes == frozen_bytes
    planted_path = ROOT / "evaluator/hidden/planted_witness.json"
    planted = evaluator.read_witness(planted_path)
    planted_result = evaluator.evaluate(planted_path)
    assert planted_result["passed"] and planted_result["valid"]
    assert all(planted_result[key] == 1 for key in ("core_score", "worst_family_score", "resource_score"))
    freeze = json.loads((ROOT / "evaluator/hidden/freeze.json").read_text())
    assert hashlib.sha256(planted_path.read_bytes()).hexdigest() == freeze["planted_witness_sha256"]
    for case in suite["instances"]:
        independent_replay(case, planted["circuits"][case["id"]])
        assert set(case["required_parities"]).isdisjoint(case["target_rows"])
        assert all(mask.bit_count() >= 3 for mask in case["required_parities"])
        for mask, (prefix, wire) in freeze["audits"][case["id"]]["obligation_locations"].items():
            rows = [1 << index for index in range(case["n"])]
            for control, target in planted["circuits"][case["id"]][:prefix]:
                rows[target] ^= rows[control]
            assert rows[wire] == int(mask)
    baseline_witness = baseline.synthesize(suite)
    baseline_result = evaluator.evaluate_witness(baseline_witness)
    assert baseline_result["valid"] and not baseline_result["passed"]
    assert baseline_result["core_score"] == 0
    for case in suite["instances"]:
        independent_replay(case, baseline_witness["circuits"][case["id"]])
    first = suite["instances"][0]
    case_id = first["id"]
    negatives = {}

    def reject(name, witness, semantic=False):
        result = evaluator.evaluate_witness(witness)
        assert not result["passed"], name
        if semantic:
            assert not result["valid"], name
        negatives[name] = result
        return result

    changed = copy.deepcopy(planted)
    changed["circuits"][case_id].pop()
    reject("deleted_gate", changed, True)
    changed = copy.deepcopy(planted)
    changed["circuits"][case_id].append(first["edges"][0])
    reject("wrong_final_map", changed, True)
    changed = copy.deepcopy(planted)
    edge_set = {tuple(edge) for edge in first["edges"]}
    nonedge = next([left, right] for left in range(first["n"]) for right in range(left + 1, first["n"]) if (left, right) not in edge_set)
    changed["circuits"][case_id].extend([nonedge, nonedge])
    reject("nonedge_identity_pair", changed, True)
    changed = copy.deepcopy(planted)
    changed["circuits"][case_id].extend([first["edges"][0]] * (2 * first["max_cnots"]))
    result = reject("over_budget_identity_padding", changed)
    assert result["valid"]
    changed = copy.deepcopy(planted)
    changed["circuits"][case_id] = baseline.synthesize_case(first, include_parities=False)
    result = reject("linear_map_without_phase_obligations", changed, True)
    assert result["cases"][0]["target_matches"] and result["cases"][0]["missing_parities"]
    changed = copy.deepcopy(planted)
    del changed["circuits"][case_id]
    reject("missing_case", changed, True)
    for name, bad_gate in (("bool_endpoint", [True, 1]), ("float_endpoint", [0.0, 1]), ("negative_endpoint", [-1, 0]), ("out_of_range", [0, first["n"]]), ("self_gate", [1, 1]), ("bad_gate_arity", [0, 1, 2])):
        changed = copy.deepcopy(planted)
        changed["circuits"][case_id][0] = bad_gate
        reject(name, changed, True)
    changed = copy.deepcopy(planted)
    changed["circuits"][case_id] = [first["edges"][0]] * (evaluator.MAX_GATES + 1)
    reject("gate_safety_limit", changed, True)
    changed = copy.deepcopy(planted)
    changed["schema_version"] = True
    reject("bool_version", changed, True)
    changed = copy.deepcopy(planted)
    changed["claimed_depth"] = 1
    reject("extra_claims", changed, True)
    disjoint = {"id": "unit", "family": "unit", "n": 4, "edges": [[0, 1], [2, 3]], "target_rows": [1, 3, 4, 12], "required_parities": [3, 12], "max_cnots": 2, "max_depth": 1}
    assert evaluator.replay_case(disjoint, [[0, 1], [2, 3]])["passed"]
    tight_count = dict(disjoint, max_cnots=1, max_depth=10)
    result = evaluator.replay_case(tight_count, [[0, 1], [2, 3]])
    assert result["valid"] and result["depth_ok"] and not result["count_ok"] and not result["passed"]
    tight_depth = {"id": "unit", "family": "unit", "n": 3, "edges": [[0, 1], [0, 2]], "target_rows": [1, 3, 5], "required_parities": [3, 5], "max_cnots": 2, "max_depth": 1}
    result = evaluator.replay_case(tight_depth, [[0, 1], [0, 2]])
    assert result["valid"] and result["count_ok"] and not result["depth_ok"] and result["depth"] == 2 and not result["passed"]
    empty = {"id": "unit", "family": "unit", "n": 2, "edges": [[0, 1]], "target_rows": [1, 2], "required_parities": [1, 2], "max_cnots": 0, "max_depth": 0}
    assert evaluator.replay_case(empty, [])["passed"]
    with tempfile.TemporaryDirectory(dir=ROOT / "adversary") as temporary:
        directory = Path(temporary)
        isolated = directory / "isolated_evaluator"
        (isolated / "hidden").mkdir(parents=True)
        for name in ("frozen_instances.json", "freeze.json"):
            (isolated / "hidden" / name).write_bytes((ROOT / "evaluator/hidden" / name).read_bytes())
        original_root = evaluator.ROOT
        evaluator.ROOT = isolated
        try:
            assert evaluator.evaluate_witness(planted)["passed"]
            assert evaluator.evaluate_witness(baseline_witness)["valid"]
        finally:
            evaluator.ROOT = original_root
        target = directory / "witness.json"
        for name, data in (("duplicate_key", '{"schema_version":1,"schema_version":1,"circuits":{}}'), ("nan", '{"schema_version":NaN,"circuits":{}}'), ("infinity", '{"schema_version":Infinity,"circuits":{}}'), ("broken_json", "{"), ("deep_json", "[" * 2000 + "]" * 2000)):
            target.write_text(data)
            result = evaluator.evaluate(directory)
            assert not result["valid"] and result["core_score"] == 0
            negatives[name] = result
        target.write_bytes(b"\xff")
        assert not evaluator.evaluate(directory)["valid"]
        with target.open("wb") as stream:
            stream.truncate(evaluator.MAX_BYTES + 1)
        assert not evaluator.evaluate(directory)["valid"]
        target.unlink()
        target.symlink_to(planted_path)
        assert not evaluator.evaluate(directory)["valid"]
        target.unlink()
        os.mkfifo(target)
        assert not evaluator.evaluate(directory)["valid"]
        target.unlink()
        nested = directory / "submission"
        nested.symlink_to(planted_path.parent, target_is_directory=True)
        assert not evaluator.evaluate(directory)["valid"]
        nested.unlink()
        nested.mkdir()
        (nested / "witness.json").write_text(json.dumps(planted))
        assert evaluator.evaluate(directory)["passed"]
        assert evaluator.evaluate(nested)["passed"]
        assert evaluator.evaluate(nested / "witness.json")["passed"]
    attempts = ROOT / "attempts"
    baseline_directory = attempts / "baseline/submission"
    baseline_directory.mkdir(parents=True, exist_ok=True)
    (baseline_directory / "witness.json").write_text(json.dumps(baseline_witness, separators=(",", ":")) + "\n")
    for name, result in (("planted", planted_result), ("baseline", baseline_result), ("negative_mutations", negatives)):
        (attempts / (name + "_report.json")).write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    summary = {
        "all_checks_passed": True,
        "mutation_reports": len(negatives),
        "independent_replay_cases": 12,
        "parser_and_resource_unit_checks": True,
        "public_frozen_identical": True,
        "no_reference_circuit_dependency": True,
        "instances_sha256": freeze["instances_sha256"],
        "planted": {key: planted_result[key] for key in ("core_score", "worst_family_score", "resource_score", "valid", "passed", "reason")},
        "baseline": {key: baseline_result[key] for key in ("core_score", "worst_family_score", "resource_score", "valid", "passed", "reason")},
    }
    (attempts / "validation_report.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
