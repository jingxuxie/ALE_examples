"""Measure an explicit dense-projector failure without risking host memory."""

import json
import os
from pathlib import Path
import resource
import subprocess
import sys
import time


ROOT = Path(__file__).resolve().parent.parent
compact_atoms = 2
supercell_atoms = 64
dimension = compact_atoms * supercell_atoms**2 * 27
requested_bytes = dimension**2 * 8
limit_bytes = 8192 * 1024**2
script = (
    "import numpy as np,json; dimension=" + str(dimension) + "; "
    "print(json.dumps({'dimension':dimension}),flush=True); "
    "matrix=np.empty((dimension,dimension),dtype=np.float64); print(matrix.shape)"
)


def limit_memory():
    resource.setrlimit(resource.RLIMIT_AS, (limit_bytes, limit_bytes))
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))


started = time.monotonic()
result = subprocess.run([sys.executable, "-c", script], capture_output=True,
                        text=True, preexec_fn=limit_memory, timeout=30,
                        env=dict(os.environ, OPENBLAS_NUM_THREADS="1"))
report = {
    "case_geometry": "64-atom rocksalt cubic supercell with two compact first-index atoms",
    "baseline": "Explicit dense projector over all compact Cartesian cubic coefficients",
    "coefficient_dimension": dimension, "requested_bytes": requested_bytes,
    "address_space_limit_bytes": limit_bytes, "seconds": time.monotonic() - started,
    "returncode": result.returncode, "stdout": result.stdout, "stderr": result.stderr,
    "failed_allocation": result.returncode != 0 and "MemoryError" in result.stderr,
    "scope": "This rules out this specific dense-projector baseline, not every possible general-purpose or sparse algorithm. The measured rowwise regression baseline independently tests underidentification on native data.",
}
(ROOT / "author/dense_projector_audit.json").write_text(json.dumps(report, indent=2) + "\n")
print(json.dumps(report, indent=2))
assert report["failed_allocation"]
