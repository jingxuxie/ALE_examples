import json
import socket
import sys
from pathlib import Path

sys.stdin.read()
hidden = Path.cwd().parents[2]
results = {}
try:
    (hidden / "manifest.json").read_bytes()
    results["hidden_read_denied"] = False
except PermissionError:
    results["hidden_read_denied"] = True
try:
    (hidden / "forbidden_probe_write").write_text("violation")
    results["hidden_write_denied"] = False
except PermissionError:
    results["hidden_write_denied"] = True
try:
    socket.socket()
    results["network_denied"] = False
except PermissionError:
    results["network_denied"] = True
print(json.dumps(results))
