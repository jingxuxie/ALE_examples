import hashlib
import json
import os
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
required = ["participant/TASK.md", "participant/input", "participant/workspace", "participant/baseline",
            "evaluator/evaluate.py", "evaluator/hidden", "attempts", "champions", "adversary", "status.json"]
records = {}
for name in ["concept_1", "concept_2", "concept_3"]:
    concept = ROOT / name
    missing = [relative for relative in required if not (concept / relative).exists()]
    frozen = json.loads((concept / "evaluator/frozen.json").read_text())
    mismatches = [relative for relative, expected in frozen["sha256"].items()
                  if hashlib.sha256((concept / relative).read_bytes()).hexdigest() != expected]
    links = [str(path.relative_to(concept)) for path in (concept / "participant").rglob("*") if path.is_symlink()]
    if "sandbox_sha256" in frozen:
        if hashlib.sha256((ROOT / "authoring/sandbox.py").read_bytes()).hexdigest() != frozen["sandbox_sha256"]:
            mismatches.append("shared sandbox")
    records[name] = {"missing": missing, "frozen_mismatches": mismatches,
                     "participant_links": links, "task_words": len((concept / "participant/TASK.md").read_text().split()),
                     "mode": json.loads((concept / "evaluator/protocol.json").read_text())["mode"]}
paths_match = os.path.samefile(ROOT, Path("/home/xuandong/mnt/jingxu/ALE/tasks_v4") / ROOT.name)
passed = paths_match and all(not row["missing"] and not row["frozen_mismatches"] and not row["participant_links"]
                             for row in records.values())
result = {"passed": passed, "requested_output_path_matches": paths_match, "concepts": records,
          "runner_sha256": hashlib.sha256((ROOT.parents[1] / "run_allowlisted_codex.sh").read_bytes()).hexdigest(),
          "evaluator_isolation": json.loads((ROOT / "authoring/security_scratch/report.json").read_text())}
(ROOT / "authoring/package_audit.json").write_text(json.dumps(result, indent=2) + "\n")
print(json.dumps(result, indent=2))
if not passed:
    raise SystemExit(1)
