"""Archive actual fresh v3 and the unchanged runnable generation-one task."""

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import tarfile


PENDING = Path(__file__).resolve().parent
ROOT = PENDING.parents[1]
PAPER = ROOT.parent


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    run = PAPER / "authoring" / "runs" / "concept_1" / "v_3"
    submission = run / "frozen_submission"
    champion = ROOT / "champions" / "generation_2"
    report = json.loads((run / "evaluation.json").read_text())
    assert report["passed"] and report["core_score"] == 1 and len(report["cases"]) == 20
    files = {}
    hashes = {}
    for source in sorted(submission.rglob("*")):
        assert not source.is_symlink()
        if source.is_file():
            relative = source.relative_to(submission)
            files[champion / "frozen_submission" / relative] = source.read_text()
            hashes[str(relative)] = digest(source)
    files[champion / "solve.py"] = (submission / "solve.py").read_text()
    files[champion / "evidence" / "generation_1_evaluation.json"] = (run / "evaluation.json").read_text()
    provenance = {"archived_at": datetime.now(timezone.utc).isoformat(),
                  "source_run": "authoring/runs/concept_1/v_3", "source_sha256": hashes,
                  "source_passed": True, "core_score": 1, "worst_family_score": 1,
                  "runtime": report["runtime"], "participant_exposure": False,
                  "algorithm_changes": False, "purpose": "private adversarial search only"}
    files[champion / "provenance.json"] = json.dumps(provenance, indent=2) + "\n"
    patch = "*** Begin Patch\n"
    for path, text in files.items():
        if path.exists():
            raise FileExistsError(path)
        patch += "*** Add File: " + str(path) + "\n" + "".join("+" + line + "\n" for line in text.splitlines())
    subprocess.run(["apply_patch"], input=patch + "*** End Patch\n", text=True, check=True)
    for relative, expected in hashes.items():
        assert digest(champion / "frozen_submission" / relative) == expected
    assert digest(champion / "solve.py") == hashes["solve.py"]
    seal_path = ROOT / "evaluator" / "hidden" / "prelaunch_seal.json"
    seal = json.loads(seal_path.read_text())
    archived = {}
    sources = {}
    for relative, expected in seal["files"].items():
        source = ROOT / relative
        assert source.is_file() and not source.is_symlink() and digest(source) == expected
        name = "authoring/sandbox_runner.py" if relative == "../authoring/sandbox_runner.py" else "concept_1/" + relative
        archived[name] = expected
        sources[name] = source
    name = "concept_1/evaluator/hidden/prelaunch_seal.json"
    archived[name] = digest(seal_path)
    sources[name] = seal_path
    archive_path = PENDING / "generation_1_runnable_snapshot.tar.gz"
    if archive_path.exists():
        raise FileExistsError(archive_path)
    with tarfile.open(archive_path, "w:gz") as archive:
        for name, source in sources.items():
            archive.add(source, arcname=name, recursive=False)
    extraction = PENDING / "archived_generation_1"
    extraction.mkdir()
    with tarfile.open(archive_path, "r:gz") as archive:
        for member in archive.getmembers():
            assert member.isfile() and (extraction / member.name).resolve().is_relative_to(extraction.resolve())
        archive.extractall(extraction)
    assert all(digest(extraction / name) == expected for name, expected in archived.items())
    manifest = {"archive": archive_path.name, "archive_sha256": digest(archive_path),
                "layout": {"task_root": "concept_1", "shared_runner": "authoring/sandbox_runner.py"},
                "original_code_bytes_preserved": True, "sha256": archived}
    contents = json.dumps(manifest, indent=2) + "\n"
    patch = "*** Begin Patch\n*** Add File: " + str(PENDING / "generation_1_snapshot_manifest.json") + "\n"
    patch += "".join("+" + line + "\n" for line in contents.splitlines()) + "*** End Patch\n"
    subprocess.run(["apply_patch"], input=patch, text=True, check=True)
    print(json.dumps({"champion": str(champion), "archived_files": len(archived), "private_only": True}))


if __name__ == "__main__":
    main()
