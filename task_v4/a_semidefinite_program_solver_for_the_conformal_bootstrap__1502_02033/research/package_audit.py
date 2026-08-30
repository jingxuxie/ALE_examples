import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def inventory(directory):
    return {str(path.relative_to(directory)): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in sorted(directory.rglob("*")) if path.is_file() and "__pycache__" not in path.parts}


def main():
    reports = []
    for number in range(1, 4):
        concept = ROOT / f"concept_{number}"
        for required in ["participant/TASK.md", "participant/input", "participant/workspace", "participant/baseline",
                         "evaluator/evaluate.py", "evaluator/hidden", "attempts", "champions", "adversary", "status.json"]:
            assert (concept / required).exists(), str(concept / required)
        assert not any(path.is_symlink() for path in (concept / "participant").rglob("*"))
        state = json.loads((concept / "status.json").read_text())
        records = []
        for path in sorted((concept / "attempts").glob("v_*.metadata.json")):
            metadata = json.loads(path.read_text())
            assert "finished_utc" in metadata and metadata["participant_unchanged"] and metadata["evaluator_unchanged"]
            assert metadata["model"] == "ultima-alpha" and metadata["limit_seconds"] == 3600
            assert metadata["fresh"] and metadata["output_empty_at_launch"] and metadata["participant_read_only"]
            assert not metadata["private_artifacts_mounted"]
            packet = concept if metadata["generation"] == state.get("generation", 1) else concept / "adversary" / f"generation_{metadata['generation']}_packet"
            assert inventory(packet / "participant") == metadata["participant_hashes_before"], str(packet)
            assert inventory(packet / "evaluator") == metadata["evaluator_hashes_before"], str(packet)
            submission = concept / "attempts" / f"v_{metadata['attempt']}"
            assert inventory(submission) == metadata["submission_hashes"], str(submission)
            score = json.loads(path.with_name(path.name.replace(".metadata.json", ".score.json")).read_text())
            assert score["regular_artifact_verified"] and score["generation"] == metadata["generation"]
            records.append({"attempt": metadata["attempt"], "generation": metadata["generation"], "integrity": True})
        reports.append({"concept": concept.name, "required_structure": True, "participant_symlink_free": True,
                        "attempts": records})
    isolation = json.loads((ROOT / "research" / "isolation_audit.json").read_text())
    assert isolation["passed"]
    for runtime in (ROOT / "research").glob(".runtime-*"):
        assert not (runtime / "auth.json").exists() and not (runtime / "auth.json").is_symlink()
    certificate = ROOT / "concept_3"
    assert (certificate / "participant/input/instances.json").read_bytes() == (certificate / "evaluator/hidden/instances.json").read_bytes()
    assert (certificate / "participant/workspace/check.py").read_bytes() == (certificate / "evaluator/hidden/checker.py").read_bytes()
    validation = json.loads((certificate / "adversary/validation.json").read_text())
    assert validation["valid"] and validation["planted_witness"]["passed"]
    report = {"passed": True, "concepts": reports, "isolation_passed": True,
              "runtime_auth_links_absent": True, "retained_task_public_private_contract_matches": True,
              "retained_task_private_witness_passes": True}
    (ROOT / "research/package_audit.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
