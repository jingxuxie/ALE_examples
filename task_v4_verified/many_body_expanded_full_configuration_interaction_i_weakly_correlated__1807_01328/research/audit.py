import argparse
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--require-complete", action="store_true")
    arguments = parser.parse_args()
    reports = {}
    required = ("participant/TASK.md", "participant/input", "participant/workspace",
                "participant/baseline", "evaluator/evaluate.py", "evaluator/hidden",
                "attempts", "champions", "adversary", "status.json")
    for index in range(1, 4):
        concept = ROOT / f"concept_{index}"
        missing = [name for name in required if not (concept / name).exists()]
        symlinks = [str(path.relative_to(concept)) for path in (concept / "participant").rglob("*") if path.is_symlink()]
        launches = []
        for manifest in sorted((concept / "attempts").glob("*.launch.json")):
            record = json.loads(manifest.read_text())
            participant = Path(record.get("participant_snapshot", record["participant"]))
            mismatches = []
            for relative, expected in record["participant_sha256"].items():
                path = participant / relative
                if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != expected:
                    mismatches.append(relative)
            evaluator_mismatches = []
            for relative, expected in record.get("private_evaluator_sha256_at_launch", {}).items():
                path = Path(record["packet"]) / "evaluator" / relative
                if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != expected:
                    evaluator_mismatches.append(relative)
            prefix = manifest.name.removesuffix(".launch.json")
            complete = all((concept / "attempts" / (prefix + suffix)).is_file()
                           for suffix in (".exit.json", ".score.json"))
            launches.append({"manifest": str(manifest.relative_to(ROOT)),
                             "generation": record["generation"],
                             "attempt": record.get("attempt", record["generation"]),
                             "participant_hash_mismatches": mismatches,
                             "private_evaluator_hash_mismatches": evaluator_mismatches,
                             "private_evaluator_snapshot_recorded": "private_evaluator_sha256_at_launch" in record,
                             "completion_artifacts_present": complete,
                             "read_only_participant_flag": "--task-read-only" in record["command"],
                             "model": record["model"], "limit_seconds": record["limit_seconds"],
                             "output_initially_empty": record["output_initially_empty"],
                             "ephemeral": record["ephemeral"]})
        canonical_mismatches = []
        status = json.loads((concept / "status.json").read_text())
        if status.get("selected_packet"):
            packet = concept / status["selected_packet"]
            for name in ("participant", "evaluator"):
                for source in (packet / name).rglob("*"):
                    if source.is_file() and "__pycache__" not in source.parts:
                        destination = concept / name / source.relative_to(packet / name)
                        if not destination.is_file() or source.read_bytes() != destination.read_bytes():
                            canonical_mismatches.append(str(destination.relative_to(concept)))
        reports[concept.name] = {"missing_paths": missing, "participant_symlinks": symlinks,
                                 "canonical_snapshot_mismatches": canonical_mismatches,
                                 "launches": launches}
    valid = all(not record["missing_paths"] and not record["participant_symlinks"] and
                not record["canonical_snapshot_mismatches"] and
                all(not launch["participant_hash_mismatches"] and not launch["private_evaluator_hash_mismatches"] and
                    launch["read_only_participant_flag"] and launch["output_initially_empty"] and
                    (launch["completion_artifacts_present"] or not arguments.require_complete) and
                    launch["ephemeral"] and launch["model"] == "ultima-alpha" and launch["limit_seconds"] == 3600
                    for launch in record["launches"]) for record in reports.values())
    output = {"valid": valid, "concepts": reports,
              "completion_required": arguments.require_complete,
              "source_scope": "Model Hamiltonians; not ab initio molecular benchmarks.",
              "initial_stdin_stall_excluded_from_hardness": True}
    (ROOT / "research/package_audit.json").write_text(json.dumps(output, indent=2) + "\n")
    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
