import json
import os
from pathlib import Path
import subprocess
import time


ROOT = Path(__file__).resolve().parents[1]


def main():
    record = json.loads((ROOT / "concept_3" / "attempts" / "v_1.metadata.json").read_text())
    runtime = Path(record["runtime"])
    helpers = list((runtime / "tmp" / "arg0").glob("*/codex-linux-sandbox"))
    if not helpers:
        raise RuntimeError("Child sandbox helper not created yet")
    participant = ROOT / "concept_3" / "participant"
    scratch = ROOT / "research" / "isolation_output"
    scratch.mkdir(exist_ok=True)
    denied = ROOT / "concept_3" / "evaluator" / "hidden" / "planted_certificate.json"
    profile = {"type": "managed", "file_system": {"type": "restricted", "entries": [
        {"path": {"type": "special", "value": {"kind": "minimal"}}, "access": "read"},
        {"path": {"type": "path", "path": str(participant)}, "access": "read"},
        {"path": {"type": "path", "path": str(scratch)}, "access": "write"},
        {"path": {"type": "path", "path": str(runtime / "packages")}, "access": "read"},
        {"path": {"type": "path", "path": str(runtime / "tmp" / "arg0")}, "access": "read"},
        {"path": {"type": "path", "path": str(helpers[0].resolve())}, "access": "read"}
    ]}, "network": "restricted"}
    code = f"""
import json,pathlib,numpy,scipy,sympy,mpmath
result = {{'libraries': True}}
result['task_readable'] = pathlib.Path({str(participant / 'TASK.md')!r}).is_file()
result['private_hidden_visible'] = pathlib.Path({str(denied)!r}).exists()
result['private_alias_visible'] = pathlib.Path({str(denied).replace('/srv/home/', '/home/', 1)!r}).exists()
result['sibling_attempt_visible'] = pathlib.Path({str(ROOT / 'concept_3' / 'attempts' / 'v_1.metadata.json')!r}).exists()
result['runtime_config_visible'] = pathlib.Path({str(runtime / 'config.toml')!r}).exists()
try:
    pathlib.Path({str(participant / '__read_only_control__')!r}).write_text('control')
    result['participant_write_denied'] = False
except OSError:
    result['participant_write_denied'] = True
pathlib.Path({str(scratch / 'proof.json')!r}).write_text(json.dumps(result))
print(json.dumps(result))
"""
    command = [str(helpers[0]), "--sandbox-policy-cwd", str(participant), "--command-cwd", str(participant),
               "--permission-profile", json.dumps(profile), "--", "/usr/bin/python3", "-c", code]
    started = time.monotonic()
    result = subprocess.run(command, capture_output=True, text=True, timeout=180,
                            env=dict(os.environ, OPENBLAS_NUM_THREADS="1", PYTHONDONTWRITEBYTECODE="1"))
    report = {"returncode": result.returncode, "elapsed_seconds": time.monotonic() - started,
              "stdout": result.stdout, "stderr": result.stderr, "profile": profile}
    if result.returncode == 0:
        checks = json.loads((scratch / "proof.json").read_text())
        report["checks"] = checks
        report["passed"] = (checks["libraries"] and checks["task_readable"]
                            and checks["participant_write_denied"]
                            and not any(checks[name] for name in ["private_hidden_visible",
                                        "private_alias_visible", "sibling_attempt_visible", "runtime_config_visible"]))
    else:
        report["passed"] = False
    (ROOT / "research" / "isolation_audit.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
