from datetime import datetime, timezone
import hashlib
import importlib.metadata
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / "participant/input/runtime"), str(ROOT / "participant/input")]
from models import SPECS


def main():
    path = ROOT / "evaluator/hidden/frozen.json"
    if path.exists():
        raise RuntimeError("Already frozen; no silent retargeting")
    targets = dict(pooled_error_reduction=0.25, holdout_error_reduction=0.20, max_family_failure_ratio=1.05,
                   paired_absolute_ci95_lower_strictly_positive=True)
    limits = dict(cpu_seconds=180, wall_watchdog_seconds=900, address_bytes=6 * 1024 ** 3, cpu_cores=1)
    artifacts = []
    sources = [ROOT / "participant/input/models.py", ROOT / "participant/input/worker.py", ROOT / "participant/baseline/decoder.py"]
    for directory in [ROOT / "participant/input/cases", ROOT / "participant/input/calibration", ROOT / "evaluator/hidden/challenge", ROOT / "evaluator/hidden/holdout"]:
        sources.extend(path for path in directory.rglob("*") if path.is_file())
    for artifact in sorted(sources):
        artifacts.append(dict(path=str(artifact.relative_to(ROOT)), sha256=hashlib.sha256(artifact.read_bytes()).hexdigest()))
    frozen = dict(schema_version=1, mode="A_BASELINE_IMPROVEMENT", frozen_utc=datetime.now(timezone.utc).isoformat(),
                  fresh_runner_launched=False, shots_per_case_per_split=1024, targets=targets, limits=limits, cases=SPECS,
                  artifacts=artifacts, label_sampling="independent Bernoulli mechanism sampling; H/L parity; no selection",
                  baseline="PyMatching 2.4.0 enable_correlations=True at construction and decode_batch",
                  target_policy="Frozen before any fresh participant. Do not tune to candidate outcomes.")
    path.write_text(json.dumps(frozen, indent=2) + "\n")
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    (ROOT / "evaluator/hidden/frozen.sha256").write_text(digest + "  frozen.json\n")
    versions = {distribution.metadata["Name"]: distribution.version for distribution in importlib.metadata.distributions(path=[str(ROOT / "participant/input/runtime")])}
    (ROOT / "participant/input/runtime_versions.json").write_text(json.dumps(versions, indent=2, sort_keys=True) + "\n")
    (ROOT / "participant/input/requirements.lock").write_text("\n".join(name + "==" + version for name, version in sorted(versions.items())) + "\n")
    public = dict(targets=targets, limits=limits, challenge_shots=6144, holdout_shots=6144,
                  freeze_sha256=digest, frozen_utc=frozen["frozen_utc"])
    (ROOT / "participant/input/target.json").write_text(json.dumps(public, indent=2) + "\n")
    print(json.dumps(public, indent=2))


if __name__ == "__main__":
    main()
