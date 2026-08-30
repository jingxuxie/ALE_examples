import importlib.util
import json
import os
from pathlib import Path
import sys
import tempfile

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
temporary = HERE / "temporary"
temporary.mkdir(exist_ok=True)
tempfile.tempdir = str(temporary)
spec = importlib.util.spec_from_file_location("isolation", ROOT.parent / "authoring" / "isolation.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
result = module.run_submission(HERE / "resource_probe", ROOT / "participant", "{}\n", timeout=120)
result["host_affinity"] = sorted(os.sched_getaffinity(0))
for name in ["cpu.max", "memory.max"]:
    path = Path("/sys/fs/cgroup") / name
    if path.exists():
        result["host_" + name] = path.read_text().strip()
(HERE / "resource_probe_results.json").write_text(json.dumps(result, indent=2) + "\n")
print(json.dumps({key: value for key, value in result.items() if key != "host_affinity"}, indent=2))
if result["returncode"]:
    raise SystemExit(result["returncode"])
