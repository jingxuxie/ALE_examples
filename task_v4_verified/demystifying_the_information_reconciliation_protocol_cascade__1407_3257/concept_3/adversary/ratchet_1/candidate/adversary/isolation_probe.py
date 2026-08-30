import importlib.util
import json
import os
from pathlib import Path
import sys


json.loads(sys.stdin.readline())
for forbidden in ("/proc", "/sys", "/home", "/srv", "/etc", "/task/../evaluator",
                  "/submission/../evaluator", "/task/hidden", "/task/manifest.json"):
    assert not Path(forbidden).exists(), forbidden
assert "ALE_PRIVATE_ISOLATION_SENTINEL" not in os.environ
assert "PYTHONPATH" not in os.environ
assert importlib.util.find_spec("evaluate") is None
assert Path("/task/contract.json").is_file()
assert Path("/submission/policy.py").is_file()
try:
    Path("/task/write_probe").write_text("forbidden")
except OSError:
    pass
else:
    raise AssertionError("public input is writable")
print(json.dumps({"op": "guess", "family": "SS"}), flush=True)
sys.stdin.readline()
