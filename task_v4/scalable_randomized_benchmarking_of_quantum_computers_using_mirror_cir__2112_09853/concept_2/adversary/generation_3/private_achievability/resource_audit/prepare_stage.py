import argparse
from datetime import datetime, timezone
import difflib
import hashlib
import json
from pathlib import Path
import shutil
import subprocess


AREA = Path(__file__).resolve().parent
ROOT = AREA.parents[3]
STAGE = AREA / "staged_task"
EXPECTED_MANIFEST = "35ede7981b1fbe3beb7aff3e09fa4c0cd5ea4de05a293814b7823d2d1175fd72"
OVERLAYS = {
    "evaluator/hidden/transport.py": "transport.py",
    "evaluator/hidden/selfcheck.py": "selfcheck.py",
    "participant/workspace/transport.py": "transport.py",
    "participant/workspace/develop.py": "develop.py",
    "evaluator/hidden/cgroup_accounting.py": "cgroup_accounting.py",
    "participant/workspace/cgroup_accounting.py": "cgroup_accounting.py",
}
ALLOWED_CHANGES = set(OVERLAYS) | {"evaluator/evaluate.py", "participant/TASK.md", "participant/workspace/API.md"}


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--finalize", action="store_true")
    arguments = parser.parse_args()
    manifest_path = ROOT / "evaluator/hidden/manifest.json"
    assert digest(manifest_path) == EXPECTED_MANIFEST
    original = json.loads(manifest_path.read_text())
    for relative, expected in original["files"].items():
        assert digest(ROOT / relative) == expected
    files = sorted(set(original["files"]) | set(OVERLAYS))
    if not arguments.finalize:
        STAGE.mkdir(exist_ok=False)
        for relative in files + ["evaluator/hidden/__init__.py", "evaluator/hidden/manifest.json"]:
            source = AREA / "runtime" / OVERLAYS[relative] if relative in OVERLAYS else ROOT / relative
            target = STAGE / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target)
        return
    for relative, expected in original["files"].items():
        if relative not in ALLOWED_CHANGES:
            assert digest(STAGE / relative) == expected, relative
    corrected = dict(original)
    corrected["files"] = {relative: digest(STAGE / relative) for relative in files}
    corrected["cpu_accounting_correction"] = {
        "prepared_utc": datetime.now(timezone.utc).isoformat(),
        "previous_manifest_sha256": EXPECTED_MANIFEST,
        "kind": "Infrastructure correction, not a task generation or hardness ratchet.",
        "cause": "Bubblewrap monitor exit bypassed its PID1 wait chain; RUSAGE_CHILDREN omitted policy CPU. The earlier separate CPU check mocked rusage, and the 56 checks contained no real aggregate CPU test.",
        "repair": "Trusted parent-controlled per-episode cgroup v2 cpu.stat accounting; protected parent-only descriptors; owned-group kill, empty check, final counter and removal. Official bwrap fails closed; trusted CLI can bootstrap once into a user systemd service.",
        "unchanged": "Generation 3, 2000 shots, quality targets, physical law, priors, hidden seeds, target fingerprints, baseline/policy artifacts, 60 CPU seconds plus existing .25 accounting tolerance, 90 wall seconds, and existing per-process limits.",
        "audit_development": "Top-level public imports remain supported. Unsafe audit mode needs no cgroup filesystem or bus, labels RUSAGE_CHILDREN as inexact, and cannot certify even a perfect score.",
    }
    (STAGE / "evaluator/hidden/manifest.json").write_text(json.dumps(corrected, indent=2, sort_keys=True) + "\n")
    changed = [relative for relative in files if not (ROOT / relative).exists() or digest(ROOT / relative) != digest(STAGE / relative)]
    changed.append("evaluator/hidden/manifest.json")
    patch = ["*** Begin Patch\n"]
    for relative in changed:
        before = (ROOT / relative).read_text() if (ROOT / relative).exists() else None
        after = (STAGE / relative).read_text()
        if before is None:
            patch.extend(["*** Add File: " + relative + "\n", "".join("+" + line + "\n" for line in after.splitlines())])
        else:
            patch.append("*** Update File: " + relative + "\n")
            for line in list(difflib.unified_diff(before.splitlines(keepends=True), after.splitlines(keepends=True), n=3))[2:]:
                patch.append("@@\n" if line.startswith("@@") else line)
    patch.append("*** End Patch\n")
    patch_text = "".join(patch)
    (AREA / "promotion.patch").write_text(patch_text)
    dry_run = AREA / "promotion_dry_run"
    dry_run.mkdir(exist_ok=False)
    for relative in original["files"]:
        target = dry_run / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / relative, target)
    shutil.copyfile(manifest_path, dry_run / "evaluator/hidden/manifest.json")
    result = subprocess.run(["apply_patch"], input=patch_text, text=True, cwd=dry_run, capture_output=True, check=True)
    for relative in changed:
        assert digest(dry_run / relative) == digest(STAGE / relative), relative
    provenance = dict(prepared_utc=datetime.now(timezone.utc).isoformat(), promoted=False,
                      required_clearance="Main confirms v3 metadata finished and the original frozen generation 3 archived.",
                      source_manifest_sha256=EXPECTED_MANIFEST,
                      staged_manifest_sha256=digest(STAGE / "evaluator/hidden/manifest.json"),
                      patch_sha256=digest(AREA / "promotion.patch"), changed_paths=changed,
                      staged_file_sha256={relative: digest(STAGE / relative) for relative in changed},
                      immutable_original_files_verified=True, protected_physics_benchmark_limits_and_policy_files_unchanged=True,
                      private_apply_patch_dry_run_passed=True, dry_run_stdout=result.stdout)
    (AREA / "promotion_provenance.json").write_text(json.dumps(provenance, indent=2) + "\n")
    assert digest(manifest_path) == EXPECTED_MANIFEST
    print(json.dumps(provenance, indent=2))


if __name__ == "__main__":
    main()
