import importlib.util
import json
import os
from pathlib import Path
import sys
import time

for variable in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[variable] = "1"

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("frozen", ROOT / "evaluator" / "evaluate.py")
frozen = importlib.util.module_from_spec(spec)
spec.loader.exec_module(frozen)
instance = json.loads(Path(sys.argv[1]).read_text())
model = json.loads(Path(sys.argv[2]).read_text())
started = time.monotonic()
result = frozen.exact_score(instance, model)
result["scoring_seconds"] = time.monotonic() - started
print(json.dumps(result), flush=True)
