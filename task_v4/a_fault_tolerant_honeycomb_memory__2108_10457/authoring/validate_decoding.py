import importlib.util
import json
from pathlib import Path
import tempfile

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
module_spec = importlib.util.spec_from_file_location("decoder_evaluator", ROOT / "concept_1/evaluator/evaluate.py")
evaluator = importlib.util.module_from_spec(module_spec)
module_spec.loader.exec_module(evaluator)
checks = {}
with tempfile.TemporaryDirectory() as temporary:
    scratch = Path(temporary)
    for name, array, accepted in [
        ("correct_uint8", np.array([0, 1, 0], dtype=np.uint8), True),
        ("correct_bool", np.array([[False], [True], [False]]), True),
        ("wrong_shape", np.array([0, 1], dtype=np.uint8), False),
        ("non_binary", np.array([0, 2, 0], dtype=np.uint8), False),
        ("float_output", np.array([0.0, 1.0, 0.0]), False),
        ("object_output", np.array([0, 1, 0], dtype=object), False),
    ]:
        path = scratch / (name + ".npy")
        np.save(path, array)
        try:
            evaluator.load_prediction(path, 3)
            actual = True
        except ValueError:
            actual = False
        checks[name] = actual == accepted
    link = scratch / "link.npy"
    link.symlink_to(scratch / "correct_uint8.npy")
    try:
        evaluator.load_prediction(link, 3)
        checks["symlink_rejected"] = False
    except OSError:
        checks["symlink_rejected"] = True
    payload = scratch / "trailing.npy"
    payload.write_bytes((scratch / "correct_uint8.npy").read_bytes() + b"extra")
    try:
        evaluator.load_prediction(payload, 3)
        checks["trailing_payload_rejected"] = False
    except ValueError:
        checks["trailing_payload_rejected"] = True
evaluator.check_frozen()
checks["frozen_integrity"] = True
report = {"checks": checks, "all_passed": all(checks.values()),
          "isolation_probe": json.loads((ROOT / "authoring/security_scratch/report.json").read_text())}
(ROOT / "concept_1/evaluator/validation.json").write_text(json.dumps(report, indent=2) + "\n")
print(json.dumps(report, indent=2))
if not report["all_passed"] or not all(report["isolation_probe"].values()):
    raise SystemExit(1)
