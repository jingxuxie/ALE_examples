import json
import os
from pathlib import Path
import socket
import sys


payload = json.load(sys.stdin)
result = {}
result["submission_cwd"] = Path.cwd() == Path(__file__).resolve().parent
result["one_cpu"] = len(os.sched_getaffinity(0)) == 1
try:
    os.sched_setaffinity(0, os.sched_getaffinity(0))
    result["affinity_lock"] = "UNEXPECTED_AFFINITY_CHANGE"
except PermissionError:
    result["affinity_lock"] = "denied"
for label, name in payload["forbidden"].items():
    try:
        Path(name).read_bytes()
        result[label] = "UNEXPECTED_READ"
    except (PermissionError, FileNotFoundError):
        result[label] = "denied"
try:
    socket.socket()
    result["network"] = "UNEXPECTED_SOCKET"
except PermissionError:
    result["network"] = "denied"
Path("scratch_test").write_text("ok")
result["scratch_write"] = Path("scratch_test").read_text()
print(json.dumps(result))
