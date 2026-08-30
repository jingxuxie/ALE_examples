import argparse
import json
import os
from pathlib import Path
import socket

import numpy as np
import scipy.linalg
import sklearn


parser = argparse.ArgumentParser()
parser.add_argument("--input", type=Path)
parser.add_argument("--output", type=Path)
arguments = parser.parse_args()
inputs = json.loads(arguments.input.read_text())
readable = {}
for candidate in inputs["forbidden_paths"]:
    try:
        Path(candidate).read_bytes()
        readable[candidate] = True
    except OSError:
        readable[candidate] = False
try:
    socket.create_connection(("1.1.1.1", 443), timeout=0.5).close()
    network = True
except OSError:
    network = False
try:
    os.sched_setaffinity(0, range(384))
    affinity_change = True
except PermissionError:
    affinity_change = False
result = {"forbidden_readable": readable, "network": network, "affinity_change": affinity_change,
          "numpy": np.__version__, "sklearn": sklearn.__version__,
          "eigenvalues": scipy.linalg.eigvalsh(np.array([[1.0, 0.5], [0.5, 1.0]])).tolist()}
arguments.output.write_text(json.dumps(result))
