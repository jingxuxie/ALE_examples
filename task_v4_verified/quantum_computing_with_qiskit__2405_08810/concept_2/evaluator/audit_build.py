import argparse
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
from pathlib import Path
import platform

import networkx as nx


CONCEPT_ROOT = Path(__file__).resolve().parents[1]
FROZEN_THRESHOLDS = (
    ("mesh_22", 22, 155, 65),
    ("bridge_26", 26, 189, 66),
    ("mesh_30", 30, 227, 78),
    ("bridge_34", 34, 261, 79),
)


def encode(document):
    return (json.dumps(document, indent=2, sort_keys=True, allow_nan=False) + "\n").encode("utf-8")


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def import_evaluator():
    specification = importlib.util.spec_from_file_location("private_evaluator", CONCEPT_ROOT / "evaluator" / "evaluate.py")
    module = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(module)
    return module


def release_manifest():
    public_paths = sorted(path for path in (CONCEPT_ROOT / "participant").rglob("*") if path.is_file() and "__pycache__" not in path.parts)
    private_paths = [CONCEPT_ROOT / relative for relative in (
        "evaluator/evaluate.py", "evaluator/_checker.py", "evaluator/frozen.json",
        "evaluator/selftests.py", "evaluator/audit_build.py", "evaluator/README.md",
        "evaluator/hidden/generate_instances.py", "evaluator/hidden/instances.json",
        "evaluator/hidden/generation_metadata.json", "evaluator/hidden/seed.json",
        "evaluator/hidden/planted_solution.json", "evaluator/hidden/planted_score.json",
        "adversary/weak_baseline/solution.json", "adversary/weak_baseline/score.json",
    )]
    public_hashes = {str(path.relative_to(CONCEPT_ROOT)): hashlib.sha256(path.read_bytes()).hexdigest() for path in public_paths}
    private_hashes = {str(path.relative_to(CONCEPT_ROOT)): hashlib.sha256(path.read_bytes()).hexdigest() for path in private_paths}
    return {
        "schema_version": 1, "public_files": public_hashes, "private_files": private_hashes,
        "public_sha256": hashlib.sha256(encode(public_hashes)).hexdigest(),
        "private_sha256": hashlib.sha256(encode(private_hashes)).hexdigest(),
    }


def audit():
    evaluator = import_evaluator()
    checker, suite, manifest = evaluator.load_trusted()
    actual = tuple((target["name"], target["n_qubits"], target["max_cx"], target["max_weighted_depth"]) for target in suite["targets"])
    require(actual == FROZEN_THRESHOLDS, "Thresholds changed after generation.")
    public_suite = CONCEPT_ROOT / "participant" / "input" / "instances.json"
    private_suite = CONCEPT_ROOT / "evaluator" / "hidden" / "instances.json"
    require(public_suite.read_bytes() == private_suite.read_bytes(), "Public and private instances differ.")
    require((CONCEPT_ROOT / "participant" / "workspace" / "checker.py").read_bytes() == (CONCEPT_ROOT / "evaluator" / "_checker.py").read_bytes(), "Public and frozen checkers differ.")
    planted = evaluator.evaluate(CONCEPT_ROOT / "evaluator" / "hidden" / "planted_solution.json")
    weak_baseline = evaluator.evaluate(CONCEPT_ROOT / "adversary" / "weak_baseline" / "solution.json")
    require(planted["valid"] and planted["passed"], "Private feasibility witness does not pass.")
    require(weak_baseline["valid"] and not weak_baseline["passed"], "Weak baseline validity/failure changed.")
    require(all(result["correct"] and not result["count_ok"] and not result["depth_ok"] for result in weak_baseline["per_target"]), "Baseline must be exact and exceed both caps on all four targets.")
    selftests = json.loads((CONCEPT_ROOT / "adversary" / "selftests.json").read_text(encoding="utf-8"))
    require(selftests["passed"] and selftests["tests_run"] >= 45 and not selftests["skipped"], "Evaluator selftests are incomplete.")
    seed = json.loads((CONCEPT_ROOT / "evaluator" / "hidden" / "seed.json").read_text(encoding="utf-8"))["seed_hex"]
    witness_bytes = (CONCEPT_ROOT / "evaluator" / "hidden" / "planted_solution.json").read_bytes()
    witness = checker.load_json_bytes(witness_bytes)
    for public_path in (CONCEPT_ROOT / "participant").rglob("*"):
        if public_path.is_file():
            contents = public_path.read_bytes()
            require(seed.encode() not in contents, "Private seed leaked into participant package.")
            require(contents != witness_bytes, "Private witness leaked into participant package.")
            if public_path.suffix == ".json" and public_path.name != "instances.json":
                parsed = json.loads(contents)
                require(parsed != witness, "Semantic private witness copy leaked into participant package.")
    descriptions = []
    for target, feasible, weak in zip(suite["targets"], planted["per_target"], weak_baseline["per_target"]):
        graph = nx.Graph()
        graph.add_nodes_from(range(target["n_qubits"]))
        graph.add_edges_from(instruction[:2] for instruction in target["native_cx"])
        require(nx.is_connected(graph), "Disconnected hardware.")
        degrees = sorted({degree for vertex, degree in graph.degree()})
        require(degrees == [2, 3], "Hardware is not irregular degree-two/three.")
        descriptions.append({
            "name": target["name"], "family": target["family"], "n_qubits": target["n_qubits"],
            "undirected_edges": graph.number_of_edges(), "degrees": degrees,
            "diameter": nx.diameter(graph), "gf2_rank": checker.binary_rank(target["matrix"]),
            "matrix_density": sum(sum(row) for row in target["matrix"]) / target["n_qubits"] ** 2,
            "max_cx": target["max_cx"], "max_weighted_depth": target["max_weighted_depth"],
            "planted_cx": feasible["cx_count"], "planted_depth": feasible["weighted_depth"],
            "baseline_cx": weak["cx_count"], "baseline_depth": weak["weighted_depth"],
        })
    (CONCEPT_ROOT / "evaluator" / "hidden" / "planted_score.json").write_bytes(encode(planted))
    (CONCEPT_ROOT / "adversary" / "weak_baseline" / "score.json").write_bytes(encode(weak_baseline))
    return {
        "status": "ready_for_fresh_agent", "built_at_utc": datetime.now(timezone.utc).isoformat(),
        "python": platform.python_version(), "task_mode": "C_WITNESS",
        "fresh_agents_run": 0, "hardness_tested": False, "feasibility_verified": True,
        "thresholds_frozen": True, "targets": descriptions,
        "planted": planted, "weak_baseline": weak_baseline,
        "selftests": {"passed": selftests["passed"], "tests_run": selftests["tests_run"]},
        "private_evaluator_manifest": manifest,
        "difficulty_rationale": "Exact native word synthesis with fixed labels must simultaneously satisfy near-planted count and shallow asymmetric-duration schedules on sparse irregular graphs. Routed Gaussian elimination proves the interface works but is much longer and deeper. This is not evidence of fresh-agent failure or a proof of computational hardness.",
    }


def main():
    parser = argparse.ArgumentParser(description="Privileged concept_2 build audit; never changes resource thresholds or runs fresh agents.")
    parser.add_argument("--report", type=Path, default=CONCEPT_ROOT / "adversary" / "build_audit.json")
    parser.add_argument("--freeze-release", action="store_true", help="Create the one-time full release manifest after all tests pass.")
    arguments = parser.parse_args()
    report = audit()
    release = release_manifest()
    release_path = CONCEPT_ROOT / "evaluator" / "hidden" / "release_manifest.json"
    if arguments.freeze_release:
        with release_path.open("xb") as stream:
            stream.write(encode(release))
    else:
        require(release_path.exists(), "Initial audit needs --freeze-release.")
        require(json.loads(release_path.read_text(encoding="utf-8")) == release, "Frozen release contents changed.")
    report["release_manifest"] = str(release_path.relative_to(CONCEPT_ROOT))
    report["public_sha256"] = release["public_sha256"]
    report["private_sha256"] = release["private_sha256"]
    arguments.report.parent.mkdir(parents=True, exist_ok=True)
    arguments.report.write_bytes(encode(report))
    print(json.dumps({
        "status": report["status"], "tests_run": report["selftests"]["tests_run"],
        "baseline_core_score": report["weak_baseline"]["core_score"],
        "baseline_resource_score": report["weak_baseline"]["resource_score"],
        "planted_core_score": report["planted"]["core_score"],
        "public_sha256": release["public_sha256"], "report": str(arguments.report),
    }, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
