import collections
import hashlib
import importlib.util
import json
import math
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
specification = importlib.util.spec_from_file_location("private_exact_checker", ROOT / "evaluator/routing.py")
checker = importlib.util.module_from_spec(specification)
specification.loader.exec_module(checker)


def connected(vertices, pairs):
    adjacency = {vertex: set() for vertex in vertices}
    for first, second in pairs:
        adjacency[first].add(second)
        adjacency[second].add(first)
    visited = {next(iter(vertices))}
    pending = list(visited)
    while pending:
        for neighbor in adjacency[pending.pop()]:
            if neighbor not in visited:
                visited.add(neighbor)
                pending.append(neighbor)
    return len(visited) == len(vertices)


def main():
    targets = json.loads((ROOT / "targets.json").read_text())
    assert (targets["core_target"], targets["worst_family_target"], targets["case_seconds"], targets["suite_seconds"]) == (0.4, 0.3, 12, 360)
    certificates = json.loads((ROOT / "evaluator/hidden/certificates.json").read_text())
    metadata = json.loads((ROOT / "adversary/design.json").read_text())
    manifest = json.loads((ROOT / "evaluator/hidden/manifest.json").read_text())
    hidden = json.loads((ROOT / "evaluator/hidden/cases.json").read_text())
    assert len(certificates) == 48 and len(hidden) == 36
    assert set(collections.Counter(case["family"] for case in hidden).values()) == {6}
    records = []
    for identifier, entry in certificates.items():
        case, witness, reference = entry["case"], entry["answer"], entry["baseline_answer"]
        count = case["n"]
        assert 12 <= count <= 28 and 96 <= len(case["gates"]) <= 240
        assert sorted(case["initial"]) == list(range(count))
        edges = case["edges"]
        assert all(0 <= first < count and 0 <= second < count and first != second and
                   math.isfinite(weight) and 0.45 <= weight <= 2.8 for first, second, weight in edges)
        assert len({tuple(sorted((first, second))) for first, second, _ in edges}) == len(edges)
        assert connected(set(range(count)), [(first, second) for first, second, _ in edges])
        active = {logical for pair in case["gates"] for logical in pair}
        assert len(active) >= 8 and connected(active, case["gates"])
        interactions = {tuple(sorted(pair)) for pair in case["gates"]}
        degree = collections.Counter(logical for pair in interactions for logical in pair)
        assert len(interactions) >= 10 and max(degree.values()) >= 3
        phases = metadata[identifier]["phases"]
        for phase in phases:
            gates = case["gates"][phase["start"]:phase["end"]]
            wires = {logical for pair in gates for logical in pair}
            assert len(wires) >= 4 and connected(wires, gates)
        assert sum(bool(set(first["logical_wires"]) & set(second["logical_wires"]))
                   for first, second in zip(phases, phases[1:])) >= 2
        metrics = checker.validate(case, witness)
        baseline = checker.validate(case, reference)
        assert math.isclose(baseline["cost"], manifest["baseline"][identifier]["cost"], abs_tol=1e-8)
        improvement = 1 - metrics["cost"] / baseline["cost"]
        assert improvement >= 0.50
        assert metrics["swaps"] > 0
        for malformed in ({"operations": witness["operations"][:-1]}, {"operations": [["gate", 0], ["gate", 0]]}):
            try:
                checker.validate(case, malformed)
            except ValueError:
                pass
            else:
                raise AssertionError("checker accepted an incomplete or duplicate-gate route")
        if identifier.startswith("public_"):
            assert json.loads((ROOT / "participant/input" / f"{identifier}.json").read_text()) == case
        records.append({"id": identifier, "family": case["family"], "active_wires": len(active),
                        "coupled_phases": len(phases), "distinct_interactions": len(interactions),
                        "witness_cost": metrics["cost"], "baseline_cost": baseline["cost"],
                        "witness_improvement": improvement, "swaps": metrics["swaps"]})
    public_files = sorted(str(path.relative_to(ROOT / "participant")) for path in (ROOT / "participant").rglob("*") if path.is_file())
    expected = {"TASK.md", "input/FORMAT.md", "input/baseline_scores.json", "baseline/solve.py"}
    expected.update(f"input/{identifier}.json" for identifier in certificates if identifier.startswith("public_"))
    assert set(public_files) == expected and len(expected) == 16
    assert hashlib.sha256((ROOT / "participant/baseline/solve.py").read_bytes()).hexdigest() == manifest["baseline_sha256"]
    authoring = ROOT.parents[2] / "authoring"
    assert (authoring / "sandbox.py").is_file()
    evaluation_specification = importlib.util.spec_from_file_location("g2_evaluator_import_test", ROOT / "evaluator/evaluate.py")
    evaluation = importlib.util.module_from_spec(evaluation_specification)
    evaluation_specification.loader.exec_module(evaluation)
    assert evaluation.AUTHORING.resolve() == authoring.resolve()
    result = {"valid": True, "public_cases": 12, "hidden_cases": 36,
              "certificates_checked": len(records), "minimum_witness_improvement": min(record["witness_improvement"] for record in records),
              "all_certificates_exceed_50pct": True, "all_active_graphs_coupled": True,
              "minimum_active_wires": min(record["active_wires"] for record in records),
              "private_witnesses_not_in_participant": True, "participant_whitelist_verified": public_files,
              "shared_authoring_exact_path": str(authoring.resolve()), "shared_sandbox_import_test_passed": True,
              "quality_targets": [0.4, 0.3], "resource_limits": [12, 360], "cases": records}
    (ROOT / "validation.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({key: value for key, value in result.items() if key not in ("cases", "participant_whitelist_verified")}), flush=True)


if __name__ == "__main__":
    main()
