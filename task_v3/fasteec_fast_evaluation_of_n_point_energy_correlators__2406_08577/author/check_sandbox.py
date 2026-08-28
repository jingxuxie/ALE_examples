import json
from pathlib import Path
import subprocess

from evaluator_template import sandbox_command


root = Path(__file__).resolve().parent.parent
participant = root / "pilots" / "weighted" / "participant"
attempt = root / "author" / "sandbox_probe" / "attempt"
(attempt / "job.json").write_text(json.dumps({"task_file": str(participant / "TASK.md"), "private_file": str(root / "pilots" / "weighted" / "private" / "evaluator.py")}))
subprocess.run(sandbox_command(participant, attempt / "solve.py", attempt), check=True)
record = json.loads((attempt / "result.json").read_text())
(root / "author" / "sandbox_validation.json").write_text(json.dumps(record, indent=2))
print(json.dumps(record))
