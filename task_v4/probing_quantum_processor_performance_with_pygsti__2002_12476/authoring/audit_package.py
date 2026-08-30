import argparse
from datetime import datetime
import hashlib
import json
from pathlib import Path

from run_fresh import APPROVED_RUNNER_DIGESTS, ROOT, hashes


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--final", action="store_true")
    args = parser.parse_args()
    records = []
    final_statuses = {"solved", "hard_open_candidate", "hard_verified_achievable", "invalid", "rejected"}
    filenames = {"concept_1": "design.json", "concept_2": "witness.json", "concept_3": "predictions.json"}
    for name, filename in filenames.items():
        concept = ROOT / name
        for relative in ("participant/input", "participant/workspace", "participant/baseline", "evaluator/hidden",
                         "attempts", "champions", "adversary"):
            assert (concept / relative).is_dir(), (name, relative)
        for relative in ("participant/TASK.md", "evaluator/evaluate.py", "status.json", "freeze_manifest.json"):
            assert (concept / relative).is_file(), (name, relative)
        frozen = json.loads((concept / "freeze_manifest.json").read_text())
        for asset in ("participant", "evaluator"):
            assert not any(path.is_symlink() for path in (concept / asset).rglob("*"))
            assert hashes(concept / asset) == frozen[asset + "_sha256"], (name, asset)
        status = json.loads((concept / "status.json").read_text())
        if args.final:
            assert status["status"] in final_statuses, (name, status["status"])
        attempts = []
        for metadata_path in sorted((concept / "attempts").glob("*.run.json")):
            metadata = json.loads(metadata_path.read_text())
            assert metadata["model"] == "ultima-alpha"
            assert 0 < metadata["limit_seconds"] <= 3600
            for field in ("initial_output_empty", "task_read_only", "ephemeral", "fresh_runtime"):
                assert metadata[field] is True, (name, field)
            assert metadata["private_artifacts_available"] is False
            assert metadata["command_network_enabled"] is False
            assert metadata["web_search"] == "disabled"
            assert metadata["runner_sha256"] in APPROVED_RUNNER_DIGESTS
            runner_snapshot = ROOT / "authoring/runner_snapshots" / (metadata["runner_sha256"] + ".sh")
            assert hashlib.sha256(runner_snapshot.read_bytes()).hexdigest() == metadata["runner_sha256"]
            snapshot = ROOT / metadata["snapshot_root"] if "snapshot_root" in metadata else concept
            generation_freeze = json.loads((snapshot / "freeze_manifest.json").read_text())
            assert datetime.fromisoformat(generation_freeze["frozen_at"]) < datetime.fromisoformat(metadata["started_at"])
            for asset in ("participant", "evaluator"):
                assert hashes(snapshot / asset) == metadata[asset + "_sha256"]
                assert generation_freeze[asset + "_sha256"] == metadata[asset + "_sha256"]
            attempt = metadata_path.name.removesuffix(".run.json")
            entry = dict(attempt=attempt, status=metadata["status"], snapshot=str(snapshot.relative_to(ROOT)))
            if metadata["status"] == "finished":
                assert metadata["participant_unchanged"] and metadata["evaluator_unchanged"]
                assert metadata["elapsed_seconds"] <= 3615
                assert hashes(Path(metadata["output"])) == metadata["submission_sha256"]
                score_path = concept / "attempts" / (attempt + ".score.json")
                if args.final:
                    assert score_path.exists()
                if score_path.exists():
                    score = json.loads(score_path.read_text())
                    entry.update({key: score[key] for key in ("core_score", "worst_family_score", "passed", "valid")})
                    if score["valid"]:
                        artifact = Path(metadata["output"]) / filename
                        assert artifact.is_file() and not artifact.is_symlink()
                entry.update(elapsed_seconds=metadata["elapsed_seconds"], timed_out=metadata["timed_out"])
            elif args.final:
                raise AssertionError((name, attempt, "unfinished attempt"))
            attempts.append(entry)
        assert attempts
        champions = []
        for provenance_path in sorted((concept / "champions").glob("*/provenance.json")):
            provenance = json.loads(provenance_path.read_text())
            artifact = provenance_path.parent / filename
            assert hashlib.sha256(artifact.read_bytes()).hexdigest() == provenance["artifact_sha256"]
            assert provenance["score"]["passed"] and provenance["score"]["valid"]
            champions.append(str(provenance_path.parent.relative_to(concept)))
        records.append(dict(concept=name, status=status["status"], attempts=attempts, champions=champions,
                            current_frozen_files={asset: len(frozen[asset + "_sha256"])
                                                  for asset in ("participant", "evaluator")}))
    credential_paths = [str(path.relative_to(ROOT)) for name in ("auth.json", "config.toml")
                        for path in (ROOT / "authoring/runtimes").glob("*/" + name)]
    if args.final:
        assert not credential_paths, "credentials remain in finished runtimes"
    isolation = json.loads((ROOT / "authoring/isolation_audit.json").read_text())
    assert isolation["passed"] and all(isolation["checks"].values())
    report = dict(passed=True, final_audit=args.final, concepts=records,
                  active_runtime_credential_files=len(credential_paths), native_isolation_verified=True,
                  historical_assets_unchanged=True, submission_code_executed_by_evaluators=False)
    destination = ROOT / "authoring" / ("final_package_audit.json" if args.final else "interim_package_audit.json")
    destination.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
