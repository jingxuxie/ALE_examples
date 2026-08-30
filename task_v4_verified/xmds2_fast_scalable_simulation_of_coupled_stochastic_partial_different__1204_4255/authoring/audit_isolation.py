import json
from pathlib import Path

from isolation import run_submission


ROOT = Path(__file__).resolve().parents[1]
forbidden = [str(ROOT / "concept_1" / "evaluator" / "hidden" / "cases.json"), str(ROOT / "authoring" / "sources" / "paper.pdf"), "/home/xuandong/.codex/auth.json", "/srv/home/xuandong/.codex/auth.json"]
result = run_submission(ROOT / "authoring" / "isolation_probe", ROOT / "concept_1" / "participant", json.dumps({"forbidden": forbidden}) + "\n", timeout=30)
try:
    evidence = json.loads(result.pop("stdout"))
    passed = result["returncode"] == 0 and evidence["participant_readable"] and all(value != "READABLE" for value in evidence["forbidden_reads"].values()) and all(value != "WRITABLE" for value in evidence["forbidden_writes"].values()) and evidence["network"] != "CONNECTED"
except (ValueError, KeyError):
    evidence = {}
    passed = False
report = {"passed": passed, "evidence": evidence, "resources": result, "note": "Submission execution audit. Fresh-agent generation uses the separate user-specified allowlisted runner and is recorded in attempts/*.run.json."}
(ROOT / "authoring" / "isolation_audit.json").write_text(json.dumps(report, indent=2) + "\n")
print(json.dumps(report, indent=2))
if not passed:
    raise SystemExit(1)
