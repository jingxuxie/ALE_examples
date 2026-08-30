import argparse
import json
import os
from pathlib import Path
import socket
import subprocess

import numpy as np
from scipy.linalg import eigh


def denied(operation):
    try:
        operation()
    except (PermissionError, FileNotFoundError):
        return True
    return False


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    arguments = parser.parse_args()
    data = json.loads(Path(arguments.input).read_text())
    canary = data["private"]
    output = Path(arguments.output)
    probes = {
        "private_read_denied": denied(lambda: Path(canary).read_bytes()),
        "private_truncate_denied": denied(lambda: os.truncate(canary, 0)),
        "alternate_mount_read_denied": denied(lambda: Path(canary.replace("/home/", "/srv/home/")).read_bytes()),
        "proc_memory_denied": denied(lambda: Path("/proc/self/mem").open("rb")),
        "participant_write_denied": denied(lambda: (Path(data["participant"]) / "unauthorized").write_text("bad")),
        "network_denied": denied(lambda: socket.socket()),
        "exec_denied": denied(lambda: subprocess.run(["/bin/true"], check=True)),
    }
    eigenvalues = eigh(np.array([[2.0, 0.5], [0.5, 1.0]]), eigvals_only=True)
    np.savez(output.parent / "roundtrip.npz", eigenvalues=eigenvalues)
    restored = np.load(output.parent / "roundtrip.npz", allow_pickle=False)["eigenvalues"]
    probes["numpy_scipy_and_output_work"] = bool(np.allclose(restored, eigenvalues))
    output.write_text(json.dumps(probes))


if __name__ == "__main__":
    main()
