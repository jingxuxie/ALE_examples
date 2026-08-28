import json
from pathlib import Path
import shutil
import subprocess
import sys


root = Path(__file__).resolve().parent.parent
reports = root / "author" / "reports"
reports.mkdir(exist_ok=True)
for kind in ["weighted", "fractional", "resolved", "ewoc"]:
    private = root / "pilots" / kind / "private"
    shutil.copyfile(root / "author" / "evaluator_template.py", private / "evaluator.py")
    baseline = root / "author" / "weak_runs" / kind
    baseline.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(root / "author" / "weak_baseline.py", baseline / "solve.py")
    command = [sys.executable, str(private / "evaluator.py"), "--solver", str(baseline / "solve.py"), "--case", "pilot_sparse", "--report", str(reports / (kind + "_weak.json"))]
    subprocess.run(command, check=True)
    command = [sys.executable, str(private / "evaluator.py"), "--reference", "--case", "pilot_sparse", "--report", str(reports / (kind + "_reference_check.json"))]
    subprocess.run(command, check=True)
print(json.dumps({"weak_baselines_and_reference_replays": "completed"}))
