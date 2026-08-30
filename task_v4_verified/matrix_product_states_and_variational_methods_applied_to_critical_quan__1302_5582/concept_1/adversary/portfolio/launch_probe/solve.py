"""Public-only startup diagnostic, not a candidate optimizer."""

import os
os.write(2, b"portfolio_launch_probe_entered\n")

import sys
sys.dont_write_bytecode = True
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"

import json
import struct
import zipfile

arguments = sys.argv[1:]
request_path = arguments[arguments.index("--request") + 1]
output_path = arguments[arguments.index("--output") + 1]
with open(request_path) as stream:
    request = json.load(stream)
dimension = request["local_dim"]
header = ("{'descr': '<f8', 'fortran_order': False, 'shape': (1, %d, 1), }" % dimension).encode("ascii")
header += b" " * ((16 - (10 + len(header) + 1) % 16) % 16) + b"\n"
prefix = b"\x93NUMPY\x01\x00" + struct.pack("<H", len(header)) + header
with zipfile.ZipFile(output_path, "w", compression=zipfile.ZIP_STORED) as archive:
    for site in range(request["n_sites"]):
        occupied = 1 if request["sector"] == "odd" and site == 0 else 0
        data = struct.pack("<" + "d" * dimension, *[float(level == occupied) for level in range(dimension)])
        archive.writestr("A%d.npy" % site, prefix + data)
os.write(2, b"portfolio_launch_probe_state_written\n")
