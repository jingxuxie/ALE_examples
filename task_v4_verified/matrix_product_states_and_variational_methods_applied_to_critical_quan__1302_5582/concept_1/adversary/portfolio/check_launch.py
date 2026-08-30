"""One public-only bwrap entry/output diagnostic with no numerical imports in the child."""

import os
import sys

sys.dont_write_bytecode = True
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FOLDER = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "evaluator"))
from sandbox_runner import run_submission

request = json.loads((ROOT / "participant/input/example_symmetric.json").read_text())
request.update(budget_seconds=6.0, wall_seconds=30.0)
result = run_submission(FOLDER / "launch_probe", ROOT / "participant", FOLDER / "launch_probe_run", request)
result["purpose"] = "public startup diagnostic only; not a solver variant or hidden score"
result["entry_log"] = (FOLDER / "launch_probe_run/stderr.log").read_text(errors="replace")
result["state_exists"] = Path(result["state_path"]).is_file()
(FOLDER / "launch_probe_report.json").write_text(json.dumps(result, indent=2) + "\n")
print(json.dumps(result, indent=2))
