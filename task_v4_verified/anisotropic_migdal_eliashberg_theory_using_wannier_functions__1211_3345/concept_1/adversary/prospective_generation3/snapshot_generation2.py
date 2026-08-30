"""Preserve the active generation byte-for-byte with its sibling sandbox runner."""

import hashlib
import json
from pathlib import Path
import tarfile
import time

SIDECAR = Path(__file__).resolve().parent
ROOT = SIDECAR.parents[1]


def main():
    started = time.process_time()
    protocol = json.loads((SIDECAR / "protocol.json").read_text())
    records = dict(protocol["active_sealed_files"])
    seal = ROOT / "evaluator/hidden/prelaunch_seal.json"
    records["evaluator/hidden/prelaunch_seal.json"] = hashlib.sha256(seal.read_bytes()).hexdigest()
    archive_path = SIDECAR / "generation_2_runnable_snapshot.tar.gz"
    extracted = SIDECAR / "archived_generation_2"
    assert not archive_path.exists() and not extracted.exists()
    contents = {}
    with tarfile.open(archive_path, "w:gz", compresslevel=1) as archive:
        for relative, expected in records.items():
            source = ROOT / relative
            assert source.is_file() and not source.is_symlink()
            assert hashlib.sha256(source.read_bytes()).hexdigest() == expected
            name = "authoring/sandbox_runner.py" if relative == "../authoring/sandbox_runner.py" else "concept_1/" + relative
            archive.add(source, arcname=name, recursive=False)
            contents[name] = expected
    extracted.mkdir()
    with tarfile.open(archive_path, "r:gz") as archive:
        for member in archive:
            assert member.isfile() and member.name in contents
            target = extracted / member.name
            assert target.resolve().is_relative_to(extracted.resolve())
            target.parent.mkdir(parents=True, exist_ok=True)
            stream = archive.extractfile(member)
            with stream:
                target.write_bytes(stream.read())
            assert hashlib.sha256(target.read_bytes()).hexdigest() == contents[member.name]
    result = {"generation": 2, "archive": archive_path.name,
              "archive_sha256": hashlib.sha256(archive_path.read_bytes()).hexdigest(),
              "files": len(contents), "sha256": contents, "cpu_seconds": time.process_time() - started,
              "shared_runner_at_expected_relative_location": True, "all_original_code_hashes_preserved": True}
    (SIDECAR / "generation_2_snapshot_manifest.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({key: value for key, value in result.items() if key != "sha256"}))


if __name__ == "__main__":
    main()
