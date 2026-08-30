"""Import this helper to locate input under main's sanitized sandbox environment."""

import os
from pathlib import Path
import sys

_candidates = []
if "RADIAL_INPUT" in os.environ:
    _candidates.append(Path(os.environ["RADIAL_INPUT"]))
_candidates.append(Path(__file__).resolve().parents[1] / "input")
_candidates.extend(Path(directory).absolute().parent / "input" for directory in sys.path if directory)
INPUT_DIR = None
for _candidate in _candidates:
    try:
        if (_candidate / "model.py").is_file() and (_candidate / "protocol.py").is_file():
            INPUT_DIR = _candidate
            break
    except OSError:
        continue
if INPUT_DIR is None:
    raise ImportError("public input unavailable; expose participant/workspace on PYTHONPATH")
sys.path.insert(0, str(INPUT_DIR))
