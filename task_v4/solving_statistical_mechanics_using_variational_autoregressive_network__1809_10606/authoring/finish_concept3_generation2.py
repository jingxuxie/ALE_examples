import os

for variable in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[variable] = "1"

from datetime import datetime, timezone
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import sys
import tempfile
import numpy as np


ROOT = Path(__file__).resolve().parents[1]
CONCEPT = ROOT / "concept_3"
GENERATION = CONCEPT / "generations/generation_2"
STRESS = CONCEPT / "adversary/champion1_cold_stress"


def write(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False))


def main():
    for name in ("attempts", "champions", "adversary", "participant/workspace", "participant/baseline"):
        (GENERATION / name).mkdir(parents=True, exist_ok=True)
    incomplete = GENERATION / "participant/baseline/source"
    if incomplete.exists():
        shutil.move(str(incomplete), str(GENERATION / "adversary/incomplete_builder_sources"))
    queries = json.loads((STRESS / "queries.json").read_text())
    identifiers = np.asarray([query["id"] for query in queries], dtype="<U24")
    assert len(queries) == 48
    shutil.copyfile(STRESS / "full_posterior/predictions.npz", GENERATION / "participant/baseline/predictions.npz")
    with np.load(STRESS / "true_probabilities.npz", allow_pickle=False) as archive:
        truth = archive["probabilities"].copy()
        assert archive["query_ids"].tolist() == identifiers.tolist()
    np.savez(GENERATION / "evaluator/hidden/labels.npz", probabilities=np.ascontiguousarray(truth, dtype="<f8"), query_ids=identifiers)
    write(GENERATION / "evaluator/hidden/scoring.json", {"families": [query["family"] for query in queries]})
    specification = importlib.util.spec_from_file_location("cold_evaluator", GENERATION / "evaluator/evaluate.py")
    evaluator = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(evaluator)
    baseline = evaluator.evaluate(GENERATION / "participant/baseline")
    assert baseline["valid"] and not baseline["passed"]
    expected = json.loads((STRESS / "full_posterior/report.json").read_text())["metrics"]
    assert max(abs(baseline["metrics"][name] - expected[name]) for name in expected) < 1e-12
    write(GENERATION / "adversary/baseline_score.json", baseline)
    checks = []
    with tempfile.TemporaryDirectory(dir=GENERATION / "adversary") as directory:
        temporary = Path(directory)
        def test(name, probabilities, ids, valid, passed=False, extra=False):
            content = {"probabilities": probabilities, "query_ids": ids}
            if extra:
                content["unexpected"] = np.zeros(1)
            np.savez(temporary / "predictions.npz", **content)
            report = evaluator.evaluate(temporary)
            assert report["valid"] == valid and report["passed"] == passed, (name, report)
            checks.append({"name": name, "passed": True})
        test("oracle_parser_and_score_control_not_inference", truth, identifiers, True, True)
        test("uniform_quality_failure", np.full((48, 64), 1 / 64), identifiers, True)
        test("old_shape_rejected", truth[:24], identifiers[:24], False)
        test("float32_rejected", truth.astype(np.float32), identifiers, False)
        test("wrong_id_dtype_rejected", truth, identifiers.astype("<U8"), False)
        test("wrong_order_rejected", truth, identifiers[::-1].copy(), False)
        test("extra_array_rejected", truth, identifiers, False, extra=True)
        for label, value in (("nan", np.nan), ("infinity", np.inf), ("zero", 0), ("negative", -1)):
            corrupted = truth.copy()
            corrupted[0, 0] = value
            test(label + "_rejected", corrupted, identifiers, False)
        test("unnormalized_rejected", truth * 0.9, identifiers, False)
    sys.path.insert(0, str(CONCEPT / "participant"))
    from transfer import model_from_edges
    with np.load(GENERATION / "evaluator/hidden/model.npz", allow_pickle=False) as archive:
        material = model_from_edges(json.loads((GENERATION / "participant/input/model.json").read_text()), archive["couplings"], archive["fields"])
    helper_spec = importlib.util.spec_from_file_location("cold_dense_check", CONCEPT / "adversary/response_stress/run_stress.py")
    helper = importlib.util.module_from_spec(helper_spec)
    helper_spec.loader.exec_module(helper)
    dense = np.asarray([helper.dense_marginal(material, query) for query in queries])
    error = float(np.max(np.abs(dense - truth)))
    assert error < 2e-12
    validation = {"valid": True, "parser_controls": checks, "parser_checks_passed": len(checks),
                  "all_48_independent_dense_transfer_max_abs": error,
                  "baseline_matches_full_9600_draw_replay": True,
                  "oracle_control_demonstrates_only_evaluator_correctness": True}
    write(GENERATION / "adversary/validation.json", validation)
    frozen = {str(path.relative_to(GENERATION)): hashlib.sha256(path.read_bytes()).hexdigest()
              for directory in (GENERATION / "participant", GENERATION / "evaluator")
              for path in sorted(directory.rglob("*")) if path.is_file() and "__pycache__" not in path.parts}
    write(GENERATION / "adversary/release_manifest.json", {"frozen_at": datetime.now(timezone.utc).isoformat(), "sha256": frozen,
          "query_selection": "All 48 preregistered cold cases, no post-score case filtering.",
          "full_replay_matches_original_replay_on_24_old_queries_max_abs": 2.6645352591003757e-15,
          "initial_champion_replay_not_bitwise_original": True})
    write(GENERATION / "status.json", {"concept": "concept_3", "generation": 2, "verification_mode": "D", "status": "built_not_tested",
          "ready": True, "known_passing_solution": False, "solvability": "unknown", "targets_frozen_before_fresh_launch": True,
          "targets": evaluator.TARGETS, "baseline": baseline, "validation": validation, "ratchet_generations": 1,
          "baseline_provenance": "Full 9600-draw native replay of the public-data-fitted fresh champion; tiny initial fit replay variation explicitly archived.",
          "frozen_at": datetime.now(timezone.utc).isoformat()})
    print(json.dumps({"ready": True, "baseline": baseline["metrics"], "checks": len(checks), "dense_error": error}))


if __name__ == "__main__":
    main()
