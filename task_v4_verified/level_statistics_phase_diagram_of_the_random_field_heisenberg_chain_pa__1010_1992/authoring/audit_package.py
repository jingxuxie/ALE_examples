import argparse
from collections import Counter
from datetime import datetime
import hashlib
import json
import math
from pathlib import Path

from run_attempt import tree_digest


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def field_orbit(fields):
    center = math.fsum(fields) / len(fields)
    centered = [value - center for value in fields]
    variants = []
    for direction in (centered, centered[::-1]):
        for shift in range(len(fields)):
            rotated = direction[shift:] + direction[:shift]
            for sign in (-1, 1):
                variants.append(tuple(round(sign * value, 10) for value in rotated))
    return min(variants)


def check_freeze(source, generation):
    freeze = json.loads((source / "adversary" / ("generation_" + str(generation) + "_freeze.json")).read_text())
    current = {str(path.relative_to(source)) for directory in ("participant", "evaluator")
               for path in (source / directory).rglob("*") if path.is_file() and "__pycache__" not in path.parts}
    assert current == set(freeze["files"]), (str(source), "frozen file set changed")
    for name, checksum in freeze["files"].items():
        assert digest(source / name) == checksum, (str(source), name, "frozen checksum changed")
    assert not any(path.is_symlink() for path in (source / "participant").rglob("*")), "Public symlink"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--final", action="store_true")
    arguments = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    checks = []
    generation_roots = {}
    for number in (1, 2, 3):
        concept = root / ("concept_" + str(number))
        required = ["participant/TASK.md", "participant/input", "participant/workspace", "participant/baseline",
                    "evaluator/evaluate.py", "evaluator/hidden", "attempts", "champions", "adversary", "status.json"]
        missing = [name for name in required if not (concept / name).exists()]
        assert not missing, (concept.name, missing)
        promotion = json.loads((concept / "promotion.json").read_text()) if (concept / "promotion.json").exists() else None
        snapshots = {1: concept / "generations/generation_1" if promotion else concept}
        for candidate in (concept / "generations").glob("generation_*"):
            generation = int(candidate.name.split("_")[-1])
            if generation > 1 and (candidate / "adversary" / (candidate.name + "_freeze.json")).exists():
                snapshots[generation] = candidate
        for generation, source in snapshots.items():
            check_freeze(source, generation)
        generation_roots[number] = snapshots
        active_generation = promotion["current_generation"] if promotion else 1
        if arguments.final:
            assert active_generation == max(snapshots), "Latest scored generation is not canonical"
        for directory in ("participant", "evaluator"):
            assert tree_digest(concept / directory) == tree_digest(snapshots[active_generation] / directory)
        baseline = json.loads((snapshots[active_generation] / "adversary/baseline_score.json").read_text())
        assert baseline["valid"] and baseline["evaluator_valid"], concept.name
        attempt_checks = []
        completed_attempts = []
        for metadata_path in sorted((concept / "attempts").glob("v_*.run.json")):
            metadata = json.loads(metadata_path.read_text())
            assert metadata["model"] == "ultima-alpha" and metadata["limit_seconds"] == 3600
            assert metadata["initial_output_empty"] and not metadata["main_context_shared"]
            assert "--task-read-only" in metadata["command"]
            source = snapshots[metadata["generation"]]
            freeze = json.loads((source / "adversary" / f"generation_{metadata['generation']}_freeze.json").read_text())
            assert datetime.fromisoformat(freeze["frozen_utc"]) < datetime.fromisoformat(metadata["started_utc"])
            participant_snapshot = Path(metadata.get("participant_snapshot", metadata["participant"]))
            assert metadata["participant_sha256_before"] == tree_digest(participant_snapshot)
            if "returncode" in metadata:
                assert metadata["participant_unchanged"]
                assert metadata["submission_sha256"] == tree_digest(Path(metadata["output"]))
                score_path = metadata_path.with_name(metadata_path.name.replace(".run.json", ".score.json"))
                if arguments.final:
                    assert score_path.exists(), str(score_path)
                    report = json.loads(score_path.read_text())
                    assert report["evaluator_valid"], str(score_path)
                    completed_attempts.append((metadata, report))
            elif arguments.final:
                raise AssertionError("Attempt still running: " + str(metadata_path))
            attempt_checks.append({"attempt": metadata["attempt"], "completed": "returncode" in metadata})
        if arguments.final:
            for generation in snapshots:
                passing = [(metadata, report) for metadata, report in completed_attempts
                           if metadata["generation"] == generation and report["passed"]]
                if passing:
                    choose = min if number == 1 else max
                    metadata, report = choose(passing, key=lambda pair: pair[1]["core_score"])
                    champion = concept / "champions" / f"generation_{generation}"
                    assert tree_digest(champion / "submission") == metadata["submission_sha256"]
                    assert json.loads((champion / "score.json").read_text())["core_score"] == report["core_score"]
        checks.append({"concept": concept.name, "minimum_package": True, "frozen_generations": sorted(snapshots),
                       "current_generation": active_generation, "baseline_valid": True, "attempts": attempt_checks})
    prediction_source = generation_roots[1][1]
    hidden = [json.loads(line) for line in (prediction_source / "evaluator/hidden/test.jsonl").read_text().splitlines()]
    public = [json.loads(line) for split in ("train", "validation")
              for line in (prediction_source / "participant/input" / (split + ".jsonl")).read_text().splitlines()]
    public_fields = {tuple(case["fields"]) for case in public}
    assert len(hidden) == 320 and not any(tuple(case["fields"]) in public_fields for case in hidden)
    assert all(math.isfinite(case["f"]) and 0 <= case["f"] <= 1 for case in hidden)
    public_metadata = json.loads((prediction_source / "participant/input/data_checks.json").read_text())
    assert "test" not in public_metadata["splits"], "Hidden aggregates included in participant"
    if 2 in generation_roots[1]:
        prediction_source = generation_roots[1][2]
        hidden = [json.loads(line) for line in (prediction_source / "evaluator/hidden/test.jsonl").read_text().splitlines()]
        public = [json.loads(line) for path in (prediction_source / "participant/input").glob("*.jsonl")
                  for line in path.read_text().splitlines()]
        orbits = {field_orbit(record["fields"]) for record in public}
        hidden_orbits = [field_orbit(record["fields"]) for record in hidden]
        assert len(hidden_orbits) == len(set(hidden_orbits)) == 320
        assert not any(orbit in orbits for orbit in hidden_orbits)
        assert Counter(record["family"] for record in hidden) == Counter({family: 80 for family in
            ("iid_uniform", "ordered_blocks", "alternating_correlated", "shuffled_pairs")})
        assert all(record["L"] == 14 and math.isfinite(record["f"]) and 0 <= record["f"] <= 1 for record in hidden)
        replication_checks = json.loads((prediction_source / "adversary/replication_checks.json").read_text())
        assert replication_checks["source_and_internal_symmetry_duplicates"] == 0
    if 2 in generation_roots[3]:
        source = generation_roots[3][2]
        commitment = json.loads((source / "evaluator/hidden/commitment.json").read_text())
        assert digest(source / "evaluator/hidden/protocol.json") == commitment["private_protocol_sha256"]
        assert digest(source / "participant/input/protocol.json") == commitment["public_protocol_sha256"]
        assert commitment["private_protocol_sha256"] != commitment["public_protocol_sha256"]
        assert json.loads((source / "adversary/privileged_independent_driver.json").read_text())["passed"]
    assert json.loads((root / "authoring/physics_audit.json").read_text())["passed"]
    assert json.loads((root / "authoring/isolation_audit.json").read_text())["passed"]
    witness = json.loads((root / "concept_3/adversary/privileged_score.json").read_text())
    assert witness["passed"] and witness["valid"] and witness["evaluator_valid"]
    portfolio = json.loads((root / "concept_2/adversary/portfolio_score.json").read_text())
    assert portfolio["passed"] and portfolio["valid"] and portfolio["evaluator_valid"]
    assert json.loads((root / "concept_2/adversary/portfolio_independent_driver.json").read_text())["passed"]
    if arguments.final:
        status = json.loads((root / "status.json").read_text())
        assert status["discovery_complete"] and status["status"] == "hard_verified_achievable"
        assert status["selected_concept"] == "concept_2" and status["solvability_demonstrated"]
        assert not any(json.loads(path.read_text())["passed"] for path in (root / "concept_2/attempts").glob("*.score.json"))
        prediction_stress = json.loads((root / "concept_1/generations/generation_2/adversary/replication_champion_score.json").read_text())
        assert prediction_stress["passed"] and prediction_stress["records"] == 640
        counterexample_stress = json.loads((root / "concept_3/generations/generation_2/adversary/champion_replication_stress.json").read_text())
        assert counterexample_stress["summary"]["passes"] == counterexample_stress["summary"]["replications"] == 16
        smoke_sources = (("prediction", "concept_1/attempts/v_3.score.json"),
                         ("design", "concept_2/adversary/portfolio_score.json"),
                         ("counterexample", "concept_3/attempts/v_4.score.json"))
        for name, source in smoke_sources:
            smoke = json.loads((root / "authoring" / f"canonical_{name}_smoke.json").read_text())
            expected = json.loads((root / source).read_text())
            assert smoke["passed"] and smoke["valid"] and smoke["evaluator_valid"]
            for key in ("core_score", "worst_family_score"):
                assert abs(smoke[key] - expected[key]) < 1e-10
    result = {"passed": True, "final": arguments.final, "concept_count": 3, "verification_modes": ["D", "C", "B"],
              "package_checks": checks, "hidden_prediction_data_disjoint": True,
              "independent_physics_audit_passed": True, "isolation_audit_passed": True,
              "privileged_counterexample_reproduced": True}
    destination = root / "authoring" / ("final_audit.json" if arguments.final else "preliminary_audit.json")
    destination.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result), flush=True)


if __name__ == "__main__":
    main()
