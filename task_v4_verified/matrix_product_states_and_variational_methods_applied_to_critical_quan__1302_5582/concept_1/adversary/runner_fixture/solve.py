import argparse
import json
from pathlib import Path
import socket
import subprocess

import numpy as np


parser = argparse.ArgumentParser()
parser.add_argument("--request", required=True)
parser.add_argument("--output", required=True)
arguments = parser.parse_args()
request = json.loads(Path(arguments.request).read_text())
scenario = request["probe_scenario"]
if scenario == "isolation":
    assert not Path(request["private_canary"]).exists()
elif scenario == "process":
    try:
        subprocess.run(["/usr/bin/true"], check=True)
    except PermissionError:
        pass
    else:
        raise RuntimeError("subprocess restriction absent")
elif scenario == "network":
    try:
        socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    except PermissionError:
        pass
    else:
        raise RuntimeError("socket restriction absent")
elif scenario == "spin":
    while True:
        pass
elif scenario == "symlink":
    Path(arguments.output).symlink_to(request["private_canary"])
    raise SystemExit(0)
elif scenario == "malformed":
    Path(arguments.output).write_text("not an NPZ")
    raise SystemExit(0)
tensors = {}
for site in range(request["n_sites"]):
    tensor = np.zeros((1, request["local_dim"], 1))
    tensor[0, 0, 0] = 1.0
    tensors["A" + str(site)] = tensor
np.savez(arguments.output, **tensors)
