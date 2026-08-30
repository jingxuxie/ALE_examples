import hashlib
import json
import math
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    results = []
    artifact = json.loads((ROOT / "participant/baseline/control.json").read_text())
    canonical_hash = hashlib.sha256(json.dumps(artifact, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()
    for path in (ROOT / "participant/baseline/score.json", ROOT / "attempts/baseline_evaluation.json"):
        score = json.loads(path.read_text())
        assert score["artifact_canonical_sha256"] == canonical_hash
        assert score["valid"] and not score["passed"], score["reason"]
        for key in ("core_score", "worst_family_score", "runtime_score", "resource_score"):
            assert math.isfinite(score[key]) and 0 <= score[key] <= 1
    with tempfile.TemporaryDirectory(dir=ROOT / "adversary") as temporary:
        directory = Path(temporary)
        payloads = {
            "empty": "{}",
            "duplicate": '{"schema_version":1,"schema_version":1,"controls":{}}',
            "nan": json.dumps(artifact).replace('"center": [0.0', '"center": [NaN', 1),
            "overflow": json.dumps(artifact).replace('"center": [0.0', '"center": [1e999', 1),
            "oversize": " " * 65537,
            "executable": "raise RuntimeError('this is data, not a program')"
        }
        environment = dict(os.environ, PYTHONPATH=str(ROOT / "participant/workspace"))
        for name, payload in payloads.items():
            path = directory / (name + ".json")
            path.write_text(payload)
            process = subprocess.run([sys.executable, "-I", str(ROOT / "evaluator/evaluate.py"), "--artifact", str(path)], env=environment, capture_output=True, text=True, timeout=20)
            assert process.returncode == 2, (name, process.stdout, process.stderr)
            score = json.loads(process.stdout)
            assert score["valid"] is False and score["passed"] is False
            assert score["core_score"] == 0.0 and score["worst_family_score"] == 0.0
            assert score["reason"]
            for key in ("core_score", "worst_family_score", "runtime_score", "resource_score"):
                assert math.isfinite(score[key])
            results.append({"case": name, "returncode": process.returncode, "reason": score["reason"]})
    output = {"passed": True, "artifact_canonical_sha256": canonical_hash, "fresh_agents_run": 0, "malformed_cli_results": results}
    (ROOT / "adversary/cli_validation.json").write_text(json.dumps(output, indent=2) + "\n")
    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
