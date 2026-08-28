import argparse
import json
from pathlib import Path
import socket


parser = argparse.ArgumentParser()
parser.add_argument("--input", type=Path, required=True)
parser.add_argument("--output", type=Path, required=True)
arguments = parser.parse_args()
job = json.loads(arguments.input.read_text())
record = {"allowed_task_read": bool(Path(job["task_file"]).read_text())}
try:
    Path(job["private_file"]).read_bytes()
    record["private_read_blocked"] = False
except OSError:
    record["private_read_blocked"] = True
connection = socket.socket()
connection.settimeout(0.2)
try:
    connection.connect(("1.1.1.1", 443))
    record["network_blocked"] = False
except OSError:
    record["network_blocked"] = True
finally:
    connection.close()
arguments.output.write_text(json.dumps(record))
if not all(record.values()):
    raise RuntimeError("Isolation probe failed")
