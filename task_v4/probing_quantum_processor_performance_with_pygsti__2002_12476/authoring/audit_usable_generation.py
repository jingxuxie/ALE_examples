import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile

import numpy as np


ROOT = Path(__file__).resolve().parents[1] / "concept_1"
EVIDENCE = ROOT / "adversary/generation_2"


def main():
    specification = importlib.util.spec_from_file_location("usable_score", ROOT / "evaluator/evaluate.py")
    evaluator = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(evaluator)
    sys.path.insert(0, str(ROOT / "participant/workspace"))
    from physics import FAMILIES, fisher_features, load_assets
    candidates, contract = load_assets(ROOT / "participant")
    private_contract = json.loads((ROOT / "evaluator/hidden/contract.json").read_text())
    assert contract == private_contract
    assert contract["generation"] == 2 and contract["lost_circuits"] == 3
    assert contract["target_core_score"] == .25 and contract["target_worst_family_score"] == .20
    numerical = json.loads((EVIDENCE / "three_loss_numerical_audit.json").read_text())
    assert numerical["passed"]
    baseline_path = ROOT / "participant/baseline/design.json"
    baseline = json.loads(baseline_path.read_text())
    counts = np.array(baseline["batches"])
    with np.load(ROOT / "evaluator/hidden/benchmark.npz", allow_pickle=False) as data:
        assert data["features"].shape == (600, 840, 14)
        assert np.isfinite(data["features"]).all()
        assert all(np.count_nonzero(data["families"] == family) == 100 for family in FAMILIES)
        for index in (0, 317, 599):
            recomputed = fisher_features(data["parameters"][index], candidates)
            assert np.allclose(recomputed, data["features"][index], rtol=1e-10, atol=1e-10)
        intact, loss, sets = evaluator.risk_profile(data["features"][:6], counts, 3, 64)
        assert np.allclose(intact, data["champion_intact_risks"][:6], rtol=1e-9)
        assert np.allclose(loss, data["champion_loss_risks"][:6], rtol=1e-9)
        assert all(len(case) == 3 for case in sets)
        expected_core = float(data["champion_intact_risks"].mean() / data["champion_loss_risks"].mean())
        expected_worst = min(float(data["champion_intact_risks"][data["families"] == family].mean() /
                                   data["champion_loss_risks"][data["families"] == family].mean()) for family in FAMILIES)
    result = evaluator.evaluate(baseline_path)
    assert result["valid"] and not result["passed"]
    assert abs(result["core_score"] / expected_core - 1) < 1e-8
    assert abs(result["worst_family_score"] / expected_worst - 1) < 1e-8
    assert abs(result["intact_mean_ratio"] - 1) < 1e-9
    malformed = [dict(batches=[0] * 840), dict(batches=[48] * 840), dict(batches=[True] * 840),
                 dict(batches=[0.] * 840), dict(batches=[-1] * 840), dict(batches=[1]),
                 dict(batches=[10 ** 100] * 840), dict(baseline, extra=1)]
    with tempfile.TemporaryDirectory() as temporary:
        path = Path(temporary) / "design.json"
        for document in malformed:
            path.write_text(json.dumps(document))
            assert not evaluator.evaluate(path)["valid"]
        for document in ('{"batches":[],"batches":[]}', '{"batches":[NaN]}', 'null', '[]', ' ' * 100001):
            path.write_text(document)
            assert not evaluator.evaluate(path)["valid"]
        alias = Path(temporary) / "alias.json"
        alias.symlink_to(baseline_path)
        assert not evaluator.evaluate(alias)["valid"]
        subprocess.run([sys.executable, str(ROOT / "participant/baseline/solve.py"), "--output", str(path)], check=True)
        assert path.read_bytes() == baseline_path.read_bytes()
    for relative in ("workspace/physics.py", "workspace/resilience.py", "input/candidates.json"):
        assert (ROOT / "participant" / relative).read_bytes() == (ROOT / "generations/generation_1/participant" / relative).read_bytes()
    report = dict(passed=True, physical_model_unchanged=True, exhaustive_loss_algorithm_unchanged=True,
                  core_and_family_score_formula_verified=True, six_equally_weighted_regimes=True,
                  hidden_operating_points=600, malformed_or_symlink_cases=14,
                  independently_regenerated_feature_sets=3, baseline_runnable=True,
                  independent_rank_three_relative_error=numerical["independent_rank_three_relative_error"],
                  baseline_score={key: result[key] for key in ("core_score", "worst_family_score", "intact_mean_ratio", "valid", "passed")})
    (EVIDENCE / "evaluator_audit.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
