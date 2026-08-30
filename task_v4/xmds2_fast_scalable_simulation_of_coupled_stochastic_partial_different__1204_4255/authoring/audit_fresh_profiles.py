import argparse
from datetime import datetime, timezone
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser()
parser.add_argument("--output", type=Path, default=ROOT / "authoring" / "fresh_isolation_audit.json")
options = parser.parse_args()
records = []
for entry in Path("/proc").iterdir():
    if not entry.name.isdecimal():
        continue
    try:
        arguments = (entry / "cmdline").read_bytes().decode().split("\0")
        if not arguments or not arguments[0].endswith("codex-linux-sandbox"):
            continue
        if "--sandbox-policy-cwd" not in arguments or "--permission-profile" not in arguments:
            continue
        directory = arguments[arguments.index("--sandbox-policy-cwd") + 1]
        if ROOT.name not in directory or not directory.endswith("/participant"):
            continue
        profile = json.loads(arguments[arguments.index("--permission-profile") + 1])
        records.append({"pid": int(entry.name), "policy_directory": directory, "profile": profile})
    except (OSError, ValueError, UnicodeError):
        continue

safe = bool(records)
for record in records:
    profile = record["profile"]
    safe = safe and profile.get("network") == "restricted"
    entries = profile.get("file_system", {}).get("entries", [])
    paths = []
    for item in entries:
        specification = item.get("path", {})
        if specification.get("type") == "path":
            path = specification.get("path", "")
            paths.append(path)
            if ROOT.name in path:
                allowed = "/participant" in path or "/attempts/v_" in path
                safe = safe and allowed and "/evaluator" not in path and "/adversary" not in path and "/champions" not in path
        elif specification.get("value", {}).get("kind") == "root":
            safe = False
    record["path_entries"] = paths

report = {"passed": bool(safe), "captured_at": datetime.now(timezone.utc).isoformat(), "active_sandbox_profiles": records, "scope": "Actual running fresh-agent tool sandbox profiles, not an evaluator proxy."}
options.output.write_text(json.dumps(report, indent=2) + "\n")
print(json.dumps({"passed": bool(safe), "profiles": len(records)}, indent=2))
if not safe:
    raise SystemExit(1)
