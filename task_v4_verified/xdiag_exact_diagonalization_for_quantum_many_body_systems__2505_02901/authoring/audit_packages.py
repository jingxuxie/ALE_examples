import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def hashes(directory):
    return {str(path.relative_to(directory)): hashlib.sha256(path.read_bytes()).hexdigest() for path in sorted(directory.rglob("*")) if path.is_file() and "__pycache__" not in path.parts}


def main():
    concepts = [ROOT / f"concept_{index}" for index in (1, 2, 3)]
    packages = list(concepts)
    for concept in concepts:
        packages.extend(sorted((concept / "generations").glob("generation_*")))
    results = []
    for package in packages:
        participant = package / "participant"
        symlinks = [str(path.relative_to(participant)) for path in participant.rglob("*") if path.is_symlink()]
        assert not symlinks
        required = ["participant/TASK.md", "participant/input", "participant/workspace", "participant/baseline", "evaluator/evaluate.py", "evaluator/hidden", "attempts", "champions", "adversary", "status.json"]
        missing = [name for name in required if not (package / name).exists()]
        assert not missing, (package, missing)
        current = hashes(participant)
        attempts = []
        for metadata_path in sorted((package / "attempts").glob("*.run.json")):
            metadata = json.loads(metadata_path.read_text())
            unchanged = current == metadata["participant_sha256"]
            assert unchanged, str(metadata_path)
            assert metadata["participant_read_only"] and metadata["output_initially_empty"]
            assert metadata["model"] == "ultima-alpha" and metadata["time_limit_seconds"] == 3600
            attempts.append({"metadata": str(metadata_path.relative_to(ROOT)), "participant_unchanged": unchanged, "initially_empty_output": True, "time_limit_seconds": 3600, "model": metadata["model"]})
        results.append({"package": str(package.relative_to(ROOT)), "required_layout_present": True, "participant_symlinks": symlinks, "participant_files": len(current), "attempts": attempts})
    public_parameters = {tuple(example["parameters"]) for example in json.loads((ROOT / "concept_3/participant/input/development.json").read_text())}
    hidden_parameters = {tuple(case["parameters"]) for case in json.loads((ROOT / "concept_3/evaluator/hidden/devices.json").read_text())}
    assert not public_parameters.intersection(hidden_parameters)
    report = {"passed": True, "concept_count": 3, "verification_modes": ["A", "C", "E"], "packages": results, "original_spectroscopy_development_hidden_parameter_overlap": 0, "runner_sha256": hashlib.sha256((ROOT.parents[1] / "run_allowlisted_codex.sh").read_bytes()).hexdigest(), "isolation_evidence": {"fleet": "concept_1/adversary/validation_report.json", "spectroscopy": "concept_3/adversary/protocol_validation.json", "pulse": "JSON-only checker executes no submitted code; fresh isolation uses the same allowlisted runner"}}
    (ROOT / "authoring/package_audit.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"passed": True, "packages": len(results), "attempts": sum(len(result["attempts"]) for result in results)}))


if __name__ == "__main__":
    main()
