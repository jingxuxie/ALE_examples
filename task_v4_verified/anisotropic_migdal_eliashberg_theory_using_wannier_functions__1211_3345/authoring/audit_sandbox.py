import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile


ROOT = Path(__file__).resolve().parents[1]


def audit():
    canary = ROOT / "authoring" / "private_isolation_canary.txt"
    if not canary.exists():
        canary.write_text(os.urandom(32).hex() + "\n")
    results = {}
    with tempfile.TemporaryDirectory(prefix="ale-me-isolation-") as temporary:
        work = Path(temporary)
        submission = work / "submission"
        participant = work / "participant"
        scratch = work / "scratch"
        for directory in (submission, participant, scratch):
            directory.mkdir()
        input_path = scratch / "input.json"
        input_path.write_text(json.dumps({"private": str(canary), "participant": str(participant)}))
        probe = ROOT / "authoring" / "sandbox_probe.py"
        (submission / "solve.py").write_bytes(probe.read_bytes())
        command = [sys.executable, str(ROOT / "authoring" / "sandbox_runner.py"),
                   "--submission", str(submission), "--participant", str(participant),
                   "--input", str(input_path), "--output", str(scratch / "output.json"),
                   "--scratch", str(scratch), "--cpu-seconds", "30"]
        process = subprocess.run(command, capture_output=True, text=True, timeout=240)
        results.update(returncode=process.returncode, stderr=process.stderr, stdout=process.stdout)
        if (scratch / "output.json").exists():
            results["probes"] = json.loads((scratch / "output.json").read_text())
        probes = results.get("probes", {})
        results["passed"] = process.returncode == 0 and probes and all(probes.values())
    results["canary_sha256"] = hashlib.sha256(canary.read_bytes()).hexdigest()
    (ROOT / "authoring" / "isolation_audit.json").write_text(json.dumps(results, indent=2) + "\n")
    print(json.dumps(results, indent=2))
    if not results["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    audit()
