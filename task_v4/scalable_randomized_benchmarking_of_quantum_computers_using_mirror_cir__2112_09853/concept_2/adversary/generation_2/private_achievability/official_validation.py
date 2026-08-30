import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys


AREA = Path(__file__).resolve().parent
ROOT = AREA.parents[2]
EXPECTED_MANIFEST = "8f4433401c41e825d29c4643d88a65fd70fea7e9c901dd998c5d327fc3f1d24a"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--variant", required=True)
    arguments = parser.parse_args()
    artifact = AREA / "policies" / arguments.variant
    assert artifact.is_dir() and artifact.resolve().parent == (AREA / "policies").resolve()
    manifest_path = ROOT / "evaluator/hidden/manifest.json"
    assert digest(manifest_path) == EXPECTED_MANIFEST
    manifest = json.loads(manifest_path.read_text())
    for relative, expected in manifest["files"].items():
        assert digest(ROOT / relative) == expected, relative
    confirmations = [json.loads(path.read_text()) for path in sorted(AREA.glob("confirmation_*.json"))]
    matching = [summary for report in confirmations for summary in report["summaries"]
                if summary["variant"] == arguments.variant and report["isolation"] == "bwrap"]
    assert len(matching) == 1 and matching[0]["quality_target_met"]
    assert matching[0]["valid_episodes"] == matching[0]["episodes"] == 36
    runtime = AREA / "official_runtime"
    runtime.mkdir(exist_ok=False)
    copied_files = list(manifest["files"]) + ["evaluator/hidden/manifest.json", "evaluator/hidden/__init__.py"]
    for relative in copied_files:
        target = runtime / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / relative, target)
        assert digest(target) == digest(ROOT / relative)
    selection = {
        "selected_utc": datetime.now(timezone.utc).isoformat(),
        "variant": arguments.variant,
        "selection_basis": "Independent 36-case development confirmation, before any official hidden score.",
        "confirmation": matching[0],
        "policy_files_sha256": {path.name: digest(path) for path in artifact.iterdir() if path.is_file()},
        "official_manifest_sha256": EXPECTED_MANIFEST,
        "trusted_runtime_sha256": {relative: digest(runtime / relative) for relative in copied_files},
        "relocation": "Byte-identical official evaluator, benchmark, manifest and trusted modules relocated under the exclusive private write scope; no scoring, seed, parameter, budget, policy-isolation or runtime-limit hooks.",
    }
    selection_path = AREA / "official_selection.json"
    selection_path.write_text(json.dumps(selection, indent=2) + "\n")
    environment = dict(os.environ, OPENBLAS_NUM_THREADS="1", OMP_NUM_THREADS="1", PYTHONDONTWRITEBYTECODE="1")
    report_path = AREA / "official_report.json"
    command = [sys.executable, "-B", str(runtime / "evaluator/evaluate.py"),
               "--submission", str(artifact), "--policy", "policy.py", "--isolation", "bwrap",
               "--report", str(report_path)]
    with (AREA / "official_stdout.txt").open("w") as stdout, (AREA / "official_stderr.txt").open("w") as stderr:
        result = subprocess.run(command, cwd=runtime, env=environment, stdout=stdout, stderr=stderr, timeout=1200)
    assert result.returncode == 0
    assert digest(manifest_path) == EXPECTED_MANIFEST
    for relative in copied_files:
        assert digest(ROOT / relative) == selection["trusted_runtime_sha256"][relative]
        assert digest(runtime / relative) == selection["trusted_runtime_sha256"][relative]
    for name, expected in selection["policy_files_sha256"].items():
        assert digest(artifact / name) == expected
    report = json.loads(report_path.read_text())
    selection["completed_utc"] = datetime.now(timezone.utc).isoformat()
    selection["source_and_candidate_unchanged"] = True
    selection["official_report_sha256"] = digest(report_path)
    selection["official_valid"] = report["valid"]
    selection["official_passed"] = report["passed"]
    (AREA / "official_validation_audit.json").write_text(json.dumps(selection, indent=2) + "\n")
    print(json.dumps({key: report[key] for key in ("valid", "passed", "reason", "average_family_score",
                                                 "worst_family_score", "isolation", "resources")}))


if __name__ == "__main__":
    main()
