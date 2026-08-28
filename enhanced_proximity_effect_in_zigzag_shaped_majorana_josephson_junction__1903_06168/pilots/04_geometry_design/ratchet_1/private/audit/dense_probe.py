import json
from pathlib import Path
import resource
import time

import numpy as np


started = time.monotonic()
limit = 6 * 1024 ** 3
resource.setrlimit(resource.RLIMIT_AS, (limit, limit))
dimension = 25608
record = {"dimension": dimension, "dtype": "complex128", "matrix_bytes": dimension ** 2 * 16, "address_space_limit_bytes": limit}
try:
    matrix = np.empty((dimension, dimension), dtype=np.complex128)
    record["status"] = "allocated"
except MemoryError as error:
    record.update(status="allocation_failure", error=str(error))
record["elapsed_seconds"] = time.monotonic() - started
Path(__file__).with_suffix(".json").write_text(json.dumps(record, indent=2) + "\n")
print(json.dumps(record))
