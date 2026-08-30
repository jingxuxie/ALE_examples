import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "evaluator"))
from sandbox_runner import run_submission

request = json.loads((ROOT / "participant/input/example_symmetric.json").read_text())
report = run_submission(ROOT / "adversary/sandbox_probe", ROOT / "participant",
                        ROOT / "adversary/sandbox_probe_run", request)
(ROOT / "adversary/sandbox_probe_report.json").write_text(json.dumps(report, indent=2))
print(json.dumps(report, indent=2))
if not report["process_valid"]:
    raise SystemExit(1)
