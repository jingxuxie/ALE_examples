import os
from pathlib import Path
import socket
import sys

import numpy as np
import scipy.linalg


data = np.load(sys.argv[1], allow_pickle=False)
private = Path(__file__).resolve().parents[1] / "CANDIDATES.md"
assert not private.exists(), "Private author file unexpectedly exposed"
assert not Path("/home/xuandong/.codex/config.toml").exists()
assert not Path("/srv/home/xuandong/.codex/config.toml").exists()
assert not Path("/proc/1/root/home/xuandong/.codex/config.toml").exists()
network_blocked = False
try:
    connection = socket.create_connection(("1.1.1.1", 443), timeout=0.2)
    connection.close()
except OSError:
    network_blocked = True
assert network_blocked
np.savez(sys.argv[2], eigenvalues=scipy.linalg.eigvalsh(data["matrix"]),
         private_hidden=True, network_blocked=network_blocked)
print("Numerical imports, private-file isolation and network isolation passed.")
