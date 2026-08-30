import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import numpy as np


ROOT = Path(__file__).resolve().parents[1]
GENERATION = ROOT / "concept_1/generations/generation_3"
SPECIFICATION = importlib.util.spec_from_file_location("third_evaluator_check", GENERATION / "evaluator/evaluate.py")
EVALUATOR = importlib.util.module_from_spec(SPECIFICATION)
SPECIFICATION.loader.exec_module(EVALUATOR)


def main():
    for name in ("solve.py", "regional.py", "optimization.py"):
        assert (GENERATION / "participant/baseline" / name).read_bytes() == (ROOT / "concept_1/champions/generation_2" / name).read_bytes()
    original_root, original_run = EVALUATOR.ROOT, EVALUATOR.run_case
    checks = []
    with tempfile.TemporaryDirectory(dir=GENERATION / "adversary") as temporary:
        sandbox = Path(temporary)
        hidden = sandbox / "evaluator/hidden"
        hidden.mkdir(parents=True)
        solver = sandbox / "solver"
        solver.mkdir()
        (solver / "solve.py").write_text("pass\n")
        count = 5
        couplings = np.diag(np.full(count - 1, 0.7), 1)
        couplings += couplings.T
        instance = {"n": count, "couplings": couplings.tolist(), "fields": [0.] * count}
        model = {"mixing": [1.], "weights": [np.diag(np.full(count - 1, 1.4), -1).tolist()],
                 "biases": [[0.] * count], "orders": [list(range(count))]}
        manifest = []
        for family in ("cold_cycles", "coupled_regions", "local_sectors"):
            raw = json.dumps(instance).encode()
            (hidden / (family + ".json")).write_bytes(raw)
            manifest.append({"id": family, "family": family, "file": family + ".json", "sha256": hashlib.sha256(raw).hexdigest(), "baseline_kl": 1.})
        (hidden / "manifest.json").write_text(json.dumps({"cases": manifest}))
        EVALUATOR.ROOT = sandbox
        EVALUATOR.run_case = lambda submission, instance, identifier: (model, 0.01)
        try:
            positive = EVALUATOR.evaluate(solver)
            assert positive["valid"] and positive["passed"] and positive["minimum_ess"] > 1 - 1e-12
            checks.append({"exact_chain_all_families_all_gates": True})
            model["weights"] = [np.zeros((count, count)).tolist()]
            negative = EVALUATOR.evaluate(solver)
            assert negative["valid"] and not negative["passed"] and negative["mean_kl"] > 0.04
            checks.append({"uniform_quality_failure": True})
        finally:
            EVALUATOR.ROOT, EVALUATOR.run_case = original_root, original_run
    manifest = json.loads((GENERATION / "evaluator/hidden/manifest.json").read_text())
    for case in manifest["cases"]:
        raw = (GENERATION / "evaluator/hidden" / case["file"]).read_bytes()
        assert hashlib.sha256(raw).hexdigest() == case["sha256"]
        instance = json.loads(raw)
        couplings = np.asarray(instance["couplings"])
        assert instance["n"] == 20 and np.isfinite(couplings).all() and np.all(couplings == couplings.T) and not np.any(np.diag(couplings))
    old = json.loads((ROOT / "concept_1/generations/generation_2/evaluator/hidden/manifest.json").read_text())["cases"]
    old_control = float(np.mean([case["baseline_kl"] for case in old if case["id"] in ("quartets_2", "quintets_2", "mixed_2")]))
    assert old_control > 0.06
    report = {"valid": True, "checks": checks, "all_nine_physical_cases_and_hashes_valid": True,
              "supplied_baseline_identical_to_scored_champion": True, "older_champion_local_control_mean_kl": old_control,
              "targets_fixed": EVALUATOR.TARGET, "core_numerics": "Inherited independently verified enumerator; new family/target aggregation tested here."}
    (GENERATION / "adversary/evaluator_validation.json").write_text(json.dumps(report, indent=2))
    print(json.dumps(report))


if __name__ == "__main__":
    main()
