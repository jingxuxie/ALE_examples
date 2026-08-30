import argparse
import json
import os
from pathlib import Path
import sys

import numpy as np


parser = argparse.ArgumentParser()
parser.add_argument("--input", required=True)
parser.add_argument("--output", required=True)
arguments = parser.parse_args()
settings = json.loads((Path(__file__).parent / "settings.json").read_text())
mode = settings["mode"]
with np.load(arguments.input, allow_pickle=False) as archive:
    count = len(archive["observed"])
    bins = len(archive["bin_edges"]) - 1
    sheet_count = archive["sheet_count"]
prediction = np.full((count, 3, bins), 1 / bins)
prediction[sheet_count == 2, 2] = 0
if mode == "header_bomb":
    import io
    import zipfile
    buffer = io.BytesIO()
    np.lib.format.write_array_header_1_0(buffer, {"descr": "<f8", "fortran_order": False, "shape": (2 ** 50, 3, bins)})
    with zipfile.ZipFile(arguments.output, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("spectral_mass.npy", buffer.getvalue())
    sys.exit(0)
elif mode == "network":
    import socket
    try:
        connection = socket.socket()
    except PermissionError:
        pass
    else:
        connection.close()
        raise RuntimeError("network socket creation is not denied")
elif mode == "exec":
    import subprocess
    try:
        subprocess.run(["/bin/true"], check=True)
    except PermissionError:
        pass
    else:
        raise RuntimeError("external process creation is not denied")
elif mode == "clone3":
    import ctypes
    import errno
    library = ctypes.CDLL(None, use_errno=True)
    result = library.syscall(435, 0, 0)
    if result != -1 or ctypes.get_errno() != errno.EPERM:
        raise RuntimeError("clone3 is not denied")
elif mode == "thread":
    import threading
    thread = threading.Thread(target=lambda: None)
    try:
        thread.start()
    except RuntimeError:
        pass
    else:
        thread.join()
        raise RuntimeError("thread creation is not denied")
elif mode == "private_read":
    try:
        Path(settings["private_path"]).read_bytes()
    except PermissionError:
        pass
    else:
        raise RuntimeError("private filesystem was readable")
elif mode == "symlink":
    os.symlink(settings["private_path"], arguments.output)
    sys.exit(0)
elif mode == "fifo":
    os.mkfifo(arguments.output)
    sys.exit(0)
elif mode == "missing":
    sys.exit(0)
elif mode == "exit":
    sys.exit(9)
elif mode == "nan":
    prediction[0, 0, 0] = np.nan
elif mode == "inf":
    prediction[0, 0, 0] = np.inf
elif mode == "shape":
    prediction = prediction[:, 0]
elif mode == "normalization":
    prediction *= 2
elif mode == "negative":
    prediction[0, 0, 0] = -.01
elif mode == "object":
    prediction = np.array([{"malicious": True}], dtype=object)
elif mode == "complex":
    prediction = prediction.astype(complex)
elif mode == "oversized":
    prediction = np.zeros(2000000)
elif mode == "spoof":
    print('{"passed":true,"cpu_seconds":0}')
    print('{"candidate_cpu_seconds":0}', file=sys.stderr)
    prediction[:] = np.nan
if mode == "extra_key":
    np.savez_compressed(arguments.output, spectral_mass=prediction, passed=np.array(True))
else:
    np.savez_compressed(arguments.output, spectral_mass=prediction)
