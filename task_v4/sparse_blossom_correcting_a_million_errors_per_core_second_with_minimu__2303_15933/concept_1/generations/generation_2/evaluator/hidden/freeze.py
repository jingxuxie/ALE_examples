from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.dont_write_bytecode = True
sys.path[:0] = [str(ROOT / "participant/input/runtime"), str(ROOT / "participant/input")]
from models import SPECS


def main():
    hidden = ROOT / "evaluator/hidden"
    destination = hidden / "frozen.json"
    if destination.exists():
        raise RuntimeError("Already frozen; no silent retargeting")
    sampling = json.loads((hidden / "sampling_report.json").read_text())
    qualification = json.loads((hidden / "baseline_qualification.json").read_text())
    if not json.loads((hidden / "runtime_probe.json").read_text())["all_passed"]:
        raise ValueError("Trusted CPU accounting and isolation probes must pass before freezing")
    if not sampling["complete"] or not qualification["valid"] or len(qualification["reports"]) != 2:
        raise ValueError("Complete sampling and two successful isolated baseline qualifications are required")
    baseline_cpu = max(record["execution"]["cpu_seconds"] for record in qualification["reports"])
    if baseline_cpu < 2 or not all(record["baseline_equal"] for record in qualification["reports"]):
        raise ValueError("Invalid baseline qualification")
    targets = dict(pooled_error_reduction=0.20, holdout_error_reduction=0.15, max_family_failure_ratio=1.0,
        paired_absolute_ci95_lower_strictly_positive=True)
    limits = dict(cpu_seconds=math.ceil(1.25 * baseline_cpu), wall_watchdog_seconds=900,
        address_bytes=6 * 1024 ** 3, cpu_cores=1, baseline_cpu_seconds=baseline_cpu,
        relative_cpu_multiplier=1.25, reference_policy="maximum of two pre-freeze isolated baseline CPU measurements; rounded up once")
    artifacts = []
    excluded = {"participant/input/target.json", "evaluator/hidden/frozen.json", "evaluator/hidden/frozen.sha256"}
    for directory in [ROOT / "participant", ROOT / "evaluator"]:
        for path in sorted(directory.rglob("*")):
            if path.is_symlink():
                raise ValueError("Symlink in frozen assets")
            relative = path.relative_to(ROOT).as_posix()
            if path.is_file() and relative not in excluded and "__pycache__" not in path.parts:
                artifacts.append(dict(path=relative, sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
    frozen = dict(schema_version=2, mode="A_BASELINE_IMPROVEMENT", generation=2, ratchet_index=1,
        frozen_utc=datetime.now(timezone.utc).isoformat(), fresh_runner_launched=False,
        shots_per_case_per_split=256, public_calibration_shots_per_case=256, cases=SPECS,
        targets=targets, limits=limits, artifacts=artifacts,
        baseline="Byte-identical promoted generation_1 Python/C++ decoder and native binary",
        label_sampling="Unconditional independent Bernoulli mechanism draws with H/L parity; all seeds committed before decoding; no sample selection",
        scientific_target_policy="20% pooled, 15% holdout, strict family nonregression; chosen before any fresh generation-two runner",
        reference_status="Open improvement target; no demonstrated full-target passing reference. Private controls are not Bayes bounds.")
    destination.write_text(json.dumps(frozen, indent=2) + "\n")
    digest = hashlib.sha256(destination.read_bytes()).hexdigest()
    (hidden / "frozen.sha256").write_text(digest + "  frozen.json\n")
    public = dict(targets=targets, limits=limits, challenge_shots=1536, holdout_shots=1536,
        calibration_shots=1536, family_count=3, case_count=6, freeze_sha256=digest, frozen_utc=frozen["frozen_utc"])
    (ROOT / "participant/input/target.json").write_text(json.dumps(public, indent=2) + "\n")
    print(json.dumps(public, indent=2))


if __name__ == "__main__":
    main()
