import json
import os
from pathlib import Path
import socket
import sys

import numpy as np
import scipy.linalg


forbidden = sys.argv[1]
result = {"numerical_imports": bool(np.allclose(scipy.linalg.eigvalsh(np.eye(2)), 1))}
for name, operation in (
    ("hidden_read_denied", lambda: Path(forbidden).read_text()),
    ("parent_memory_denied", lambda: Path(f"/proc/{os.getppid()}/mem").open("rb")),
    ("network_denied", lambda: socket.socket(socket.AF_INET, socket.SOCK_STREAM)),
):
    try:
        operation()
        result[name] = False
    except (PermissionError, OSError):
        result[name] = True
Path("scratch_ok").write_text("ok")
result["scratch_write"] = Path("scratch_ok").read_text() == "ok"
print(json.dumps(result))
