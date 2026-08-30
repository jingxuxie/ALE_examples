import os
import sys

sys.dont_write_bytecode = True
for variable in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ[variable] = "1"

import json
from pathlib import Path
import tempfile
import numpy as np

ROOT = Path(__file__).resolve().parent
CONCEPT = ROOT.parents[1]
tempfile.tempdir = str(ROOT / "scratch")
sys.path.insert(0, str(CONCEPT / "evaluator"))
from independent import checked_field, energy_gradient, lower_bound, read_case
from evaluate import LimitedSandbox, scratch_usage


def write_json(path, data):
    def scalar(value):
        if isinstance(value, np.generic):
            return value.item()
        raise TypeError("unsupported JSON type: " + type(value).__name__)
    Path(path).write_text(json.dumps(data, indent=2, allow_nan=False, default=scalar) + "\n")
