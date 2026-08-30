import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import numpy as np

PACKAGE = Path(__file__).resolve().parents[1]
GENERATION = PACKAGE / "concept_1" / "generations" / "generation_2"
SPEC = importlib.util.spec_from_file_location("scorer", GENERATION / "evaluator" / "evaluate.py")
SCORER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(SCORER)


def main():
    records = []
    with tempfile.TemporaryDirectory(prefix="van_g2_check_") as temporary:
        root = Path(temporary)
        hidden, submission = root / "evaluator" / "hidden", root / "submission"
        hidden.mkdir(parents=True)
        submission.mkdir()
        (submission / "solve.py").write_text("pass\n")
        count = 8
        couplings = np.zeros((count, count))
        for site in range(1, count):
            couplings[site, site - 1] = couplings[site - 1, site] = 0.4
        instance = {"n": count, "couplings": couplings.tolist(), "fields": [0.] * count}
        raw = json.dumps(instance).encode()
        cases = []
        for family in ("quartets", "quintets", "mixed"):
            (hidden / (family + ".json")).write_bytes(raw)
            cases.append({"id": family, "family": family, "file": family + ".json", "sha256": hashlib.sha256(raw).hexdigest(), "baseline_kl": 0.1})
        (hidden / "manifest.json").write_text(json.dumps({"cases": cases}))
        exact = {"mixing": [1.], "weights": [(2 * np.tril(couplings, -1)).tolist()], "biases": [[0.] * count], "orders": [list(range(count))]}
        SCORER.ROOT = root
        SCORER.run_case = lambda submitted, data, identifier: (exact, 0.01)
        positive = SCORER.evaluate(submission)
        assert positive["valid"] and positive["passed"]
        assert max(positive["family_baseline_ratios"].values()) < 1e-10
        records.append({"exact_chain_all_targets": True, "mean_kl": positive["mean_kl"]})
        uniform = {"mixing": [1.], "weights": [np.zeros_like(couplings).tolist()], "biases": [[0.] * count], "orders": [list(range(count))]}
        SCORER.run_case = lambda submitted, data, identifier: (uniform, 0.01)
        negative = SCORER.evaluate(submission)
        assert negative["valid"] and not negative["passed"]
        records.append({"uniform_fails_quality_and_ratios": True, "mean_kl": negative["mean_kl"]})
    baseline = json.loads((GENERATION / "adversary" / "baseline_report.json").read_text())
    assert baseline["valid"] and not baseline["passed"] and len(baseline["cases"]) == 9
    result = {"valid": True, "tests": records, "online_baseline_all_nine_valid": True,
              "core_numerics": "Inherited independently checked enumerator from concept1; positive and negative end-to-end goal controls passed.",
              "targets_fixed_before_fresh": SCORER.TARGET, "passing_material_solver_known": False}
    (GENERATION / "adversary" / "evaluator_validation.json").write_text(json.dumps(result, indent=2))
    print(json.dumps(result))


if __name__ == "__main__":
    main()
