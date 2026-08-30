import json
from pathlib import Path
import numpy
import scipy

assert Path("/task/TASK.md").is_file()
assert not Path("/home/xuandong/mnt/jingxu/ALE/tasks_v4/quantum_computing_with_qiskit__2405_08810/authoring/sources/paper.pdf").exists()
assert not Path("/srv/home/xuandong/.codex/auth.json").exists()
Path("/tmp/scratch").write_text("ok")
print(json.dumps({"numpy": numpy.__version__, "scipy": scipy.__version__, "hidden_denied": True}))
