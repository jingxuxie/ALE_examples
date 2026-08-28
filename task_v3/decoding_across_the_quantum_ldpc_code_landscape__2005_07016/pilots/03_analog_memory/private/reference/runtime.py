from __future__ import annotations

import os
import sys
from pathlib import Path

PILOT = Path(__file__).resolve().parents[2]
PAPER = PILOT.parents[1]
VENDOR = PAPER / "research/vendor"
SOURCE = PAPER / "research/sources/qecc"
sys.dont_write_bytecode = True
sys.path.insert(0, str(VENDOR))
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("MPLCONFIGDIR", str(PILOT / "private/reference/cache"))

