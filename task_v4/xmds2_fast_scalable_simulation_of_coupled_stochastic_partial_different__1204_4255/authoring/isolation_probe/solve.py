import json
from pathlib import Path
import socket
import sys


def main():
    specification = json.loads(sys.stdin.readline())
    paths = {}
    for path in specification["forbidden"]:
        try:
            Path(path).read_bytes()
            paths[path] = "READABLE"
        except OSError as error:
            paths[path] = type(error).__name__
    writes = {}
    for path in ["/task/probe_write", "/submission/probe_write"]:
        try:
            Path(path).write_text("bad")
            writes[path] = "WRITABLE"
        except OSError as error:
            writes[path] = type(error).__name__
    network = "CONNECTED"
    try:
        connection = socket.create_connection(("1.1.1.1", 53), timeout=0.2)
        connection.close()
    except OSError as error:
        network = type(error).__name__
    print(json.dumps({"forbidden_reads": paths, "forbidden_writes": writes, "network": network, "participant_readable": Path("/task/TASK.md").exists()}))


if __name__ == "__main__":
    main()
