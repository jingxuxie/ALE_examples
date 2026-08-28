import json
import resource
from pathlib import Path

import numpy as np


dimension = 390 * 80 * 4
limit_bytes = 12 * 1024**3
resource.setrlimit(resource.RLIMIT_AS, (limit_bytes, limit_bytes))
report = {"dimension": dimension, "complex_dense_bytes": dimension**2 * 16,
          "address_space_limit_bytes": limit_bytes, "test": "allocate one full dense complex128 Hamiltonian"}
try:
    matrix = np.empty((dimension, dimension), dtype=np.complex128)
    report["allocation_succeeded"] = True
except MemoryError:
    report["allocation_succeeded"] = False
Path(__file__).with_name("dense_probe.json").write_text(json.dumps(report, indent=2)+"\n")
print(json.dumps(report))
