import json
from pathlib import Path
import socket
import sys


denied = {}
for name, candidate in [("hidden", sys.argv[1]), ("other_task", sys.argv[2]), ("proc", "/proc/self/environ")]:
    try:
        Path(candidate).read_bytes()
        denied[name] = False
    except PermissionError:
        denied[name] = True
try:
    socket.socket()
    denied["network"] = False
except PermissionError:
    denied["network"] = True
Path(sys.argv[3]).write_text(json.dumps(denied, indent=2) + "\n")
if not all(denied.values()):
    raise SystemExit(2)
