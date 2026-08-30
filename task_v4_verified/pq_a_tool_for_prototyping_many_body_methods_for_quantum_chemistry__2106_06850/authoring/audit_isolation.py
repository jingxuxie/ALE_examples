import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    records = []
    for concept in sorted(ROOT.glob("concept_*")):
        for path in sorted((concept / "attempts").glob("v_*.launch.json")):
            launch = json.loads(path.read_text())
            generation = launch["generation"]
            snapshot = concept / "adversary" / ("generation_" + str(generation) + "_snapshot")
            original_packet = Path(launch.get("packet", concept))
            packet = snapshot if original_packet == concept and snapshot.is_dir() else original_packet
            participant = packet / "participant"
            missing = []
            changed = []
            for relative, digest in launch["participant_sha256"].items():
                asset = participant / relative
                if not asset.is_file():
                    missing.append(relative)
                elif hashlib.sha256(asset.read_bytes()).hexdigest() != digest:
                    changed.append(relative)
            command = launch["command"]
            configured = (launch["model"] == "ultima-alpha" and launch["limit_seconds"] == 3600
                          and launch["ephemeral"] and launch["participant_read_only"]
                          and launch["output_initially_empty"] and "--task-read-only" in command
                          and "3600" in command and "--model" in command)
            source_symlinks = [str(asset.relative_to(participant)) for asset in participant.rglob("*") if asset.is_symlink()]
            record = {"concept": concept.name, "launch_manifest": str(path.relative_to(ROOT)),
                      "generation": generation, "replicate": launch.get("replicate", 1),
                      "configured_isolation_valid": bool(configured),
                      "snapshot": str(packet.relative_to(ROOT)), "participant_symlinks": source_symlinks,
                      "missing_assets": missing, "changed_assets": changed,
                      "passed": bool(configured and not missing and not changed and not source_symlinks)}
            exit_path = path.with_name(path.name.replace(".launch.json", ".exit.json"))
            if exit_path.is_file():
                finish = json.loads(exit_path.read_text())
                record.update({"returncode": finish["returncode"], "wall_seconds": finish["wall_seconds"],
                               "timed_out": finish["timed_out"]})
            records.append(record)
    report = {"passed": bool(records) and all(record["passed"] for record in records),
              "fresh_session_count": len(records), "records": records,
              "scope": "Checks recorded runner flags, empty-output attestations, frozen public-file hashes, and absence of public symlinks; the supplied allowlist runner enforces filesystem/network isolation."}
    (ROOT / "authoring/isolation_audit.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"passed": report["passed"], "fresh_session_count": len(records),
                      "failed_records": [record for record in records if not record["passed"]]}, indent=2))


if __name__ == "__main__":
    main()
