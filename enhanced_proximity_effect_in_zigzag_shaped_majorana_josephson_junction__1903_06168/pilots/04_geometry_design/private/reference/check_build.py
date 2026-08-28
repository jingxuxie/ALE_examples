"""Author-only contract, provenance, and calibrated-scoring verification."""

import hashlib
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "private"))
import evaluator


def main():
    reference = ROOT / "private" / "reference"
    assert {path.name for path in ROOT.iterdir()} == {"participant", "private", "attempt"}
    assert not any((ROOT / "attempt").iterdir())
    mission = (ROOT / "participant" / "TASK.md").read_text()
    assert 85 <= len(mission.split()) <= 115
    assert all(term not in mission.lower() for term in ("arxiv", "paper", "scipost"))
    contract = (ROOT / "participant" / "input" / "CONTRACT.md").read_text()
    assert "python workspace/forward.py --input input/example.json --output /absolute/attempt/diagnostics.json" in contract
    assert "participant/workspace/" not in mission + contract
    assert "participant/input/" not in mission + contract
    assert (ROOT / "participant" / "workspace" / "physics.py").read_bytes() == (reference / "physics.py").read_bytes()
    assert hashlib.md5((reference / "author_code.zip").read_bytes()).hexdigest() == "750859a1c2c847acdff9eda0ed24873e"
    forward = evaluator.read_json(reference / "forward_check.json")
    assert forward["full_source_comparison"] and forward["absolute_gap_error_mev"] < 1e-8
    assert forward["hermiticity_error"] < 1e-10 and forward["small_particle_hole_error"] < 1e-10
    assert forward["dense_vs_block_pfaffian_agrees"] and forward["class_d_invariant"] == -1
    cases = []
    for directory in sorted((ROOT / "private" / "challenge_pool").iterdir()):
        request = evaluator.read_json(directory / "request.json")
        scenarios = evaluator.read_json(directory / "scenarios.json")
        request_id = request["request_id"]
        strong = evaluator.load_result(request, reference / f"{request_id}.json")
        weak = evaluator.geometry_arrays(request, request["baseline_geometry"])
        assert evaluator.feasibility(request, strong)["valid"]
        assert evaluator.feasibility(request, weak)["valid"]
        calibration = evaluator.read_json(reference / f"{request_id}_calibration.json")
        assert calibration["ready"] and calibration["momentum_points"] == 51
        assert calibration["scoring_rule"] == evaluator.SCORING_RULE
        assert calibration["fingerprint"] == evaluator.fingerprint(request, scenarios, strong)
        for label in ("weak", "strong"):
            rows = calibration[label]["measurements"]
            assert [row["scenario"] for row in rows] == scenarios
            assert evaluator.performance(rows)["physical_feasibility"]
            for row in rows:
                assert row["dimension"] == 4 * request["grid"]["nx"] * request["grid"]["ny"]
                assert np.allclose(row["momenta_rad"], np.linspace(0, np.pi, 51))
                assert np.isclose(row["gap_mev"], min(row["gaps_mev"]), atol=1e-12)
        weak_gap = calibration["weak"]["robust_gap_mev"]
        strong_gap = calibration["strong"]["robust_gap_mev"]
        span = strong_gap - weak_gap
        for value, expected in ((weak_gap, 0), (strong_gap, 1), (strong_gap + span, 2), (weak_gap - span, -1)):
            assert np.isclose(evaluator.normalized_score(value, weak_gap, strong_gap), expected)
        overlapping = {name: mask.copy() for name, mask in weak.items()}
        overlapping["sc_top"][0, 0] = True
        overlapping["sc_bottom"][0, 0] = True
        assert not evaluator.feasibility(request, overlapping)["valid"]
        with TemporaryDirectory(dir=ROOT / "private") as temporary:
            result_path = Path(temporary) / f"{request_id}.json"
            result_path.write_text(json.dumps({"schema_version": 1, "request_id": request_id, "geometry": {"sc_top": [[1]], "sc_bottom": [[0]]}}))
            invalid = evaluator.score_case(directory, Path(temporary), 1)
            assert not invalid["core_feasible"] and invalid["score"] == 0 and "failure" in invalid
        cases.append({"request_id": request_id, "weak_robust_gap_mev": weak_gap, "strong_robust_gap_mev": strong_gap, "weak_score": 0.0, "strong_score": 1.0})
    aggregate = evaluator.summarize_scores([
        {"request_id": "unit_high", "score": 2.0, "core_feasible": True},
        {"request_id": "unit_low", "score": -1.0, "core_feasible": True},
    ])
    assert aggregate["core_score"] == 0.5 and aggregate["worst_family_score"] == -1
    assert aggregate["core_feasibility"] == 1 and aggregate["worst_family"] == "unit_low"
    fresh = evaluator.read_json(reference / "strong_reference_check.json")
    assert fresh["complete"] and fresh["scoring_rule"] == evaluator.SCORING_RULE
    assert fresh["core_feasibility"] == 1
    assert {row["request_id"] for row in fresh["cases"]} == {row["request_id"] for row in cases}
    assert np.isclose(fresh["core_score"], 1) and np.isclose(fresh["worst_family_score"], 1)
    report = {"launch_ready": True, "participant_launched": False, "mission_words": len(mission.split()), "source_gap_mev": forward["source_gap_mev"], "source_gap_error_mev": forward["absolute_gap_error_mev"], "cases": cases, "non_saturation_checked_at": [-1, 2], "fresh_reference_core_score": fresh["core_score"], "fresh_reference_worst_family_score": fresh["worst_family_score"], "fresh_reference_core_feasibility": fresh["core_feasibility"]}
    evaluator.write_json(reference / "build_check.json", report)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
