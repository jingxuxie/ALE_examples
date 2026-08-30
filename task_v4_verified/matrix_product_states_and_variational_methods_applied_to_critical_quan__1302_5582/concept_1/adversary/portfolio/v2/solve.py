"""General budget-aware optimizer with atomic valid-state checkpoints."""

import os
import sys

sys.dont_write_bytecode = True
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
for variable in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS", "BLIS_NUM_THREADS",
                 "VECLIB_MAXIMUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ[variable] = "1"

import argparse
from array import array
import json
from pathlib import Path
import signal
import struct
import time
import zipfile


class WallDeadlineReached(Exception):
    pass


def basis_occupations(request):
    energies = []
    for site in range(request["n_sites"]):
        omega = request["omega"][site]
        spring = 0.0
        if site:
            spring += request["coupling"][site - 1]
        if site + 1 < request["n_sites"]:
            spring += request["coupling"][site]
        energies.append([0.5 * omega * (level + 0.5)
                         + 0.5 * (request["mass2"][site] + spring) * (level + 0.5) / omega
                         + request["lambda4"][site] * (2 * level * level + 2 * level + 1) / (32 * omega * omega)
                         for level in range(request["local_dim"])])
    levels = [min(range(len(local)), key=local.__getitem__) for local in energies]
    if request["sector"] != "any" and sum(levels) % 2 != int(request["sector"] == "odd"):
        _, site, level = min((local[level] - local[levels[site]], site, level)
                             for site, local in enumerate(energies)
                             for level in range(len(local)) if level % 2 != levels[site] % 2)
        levels[site] = level
    return levels


def write_basis(path, request):
    path = Path(path)
    pending = path.with_name(path.name + ".pending")
    dimension = request["local_dim"]
    header = ("{'descr': '<f8', 'fortran_order': False, 'shape': (1, %d, 1), }" % dimension).encode("ascii")
    header += b" " * ((16 - (10 + len(header) + 1) % 16) % 16) + b"\n"
    prefix = b"\x93NUMPY\x01\x00" + struct.pack("<H", len(header)) + header
    with zipfile.ZipFile(pending, "w", compression=zipfile.ZIP_STORED) as archive:
        for site, occupied in enumerate(basis_occupations(request)):
            values = array("d", [float(level == occupied) for level in range(dimension)])
            if sys.byteorder != "little":
                values.byteswap()
            archive.writestr("A%d.npy" % site, prefix + values.tobytes())
    os.replace(pending, path)


def wall_allowance(request_path, wall_seconds):
    age = time.time() - request_path.stat().st_mtime
    if not 0 <= age <= 2 * wall_seconds:
        age = 0.0
    return max(0.05, wall_seconds - age - 1.5)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--request", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    request_path = Path(args.request)
    request = json.loads(request_path.read_text())
    output = Path(args.output)
    write_basis(output, request)

    def wall_expired(signum, frame):
        raise WallDeadlineReached()

    signal.signal(signal.SIGALRM, wall_expired)
    allowance = wall_allowance(request_path, float(request["wall_seconds"]))
    signal.setitimer(signal.ITIMER_REAL, allowance)
    try:
        from contractor import save_mps
        from engine import optimize

        def checkpoint(tensors):
            pending = output.with_name(output.name + ".pending")
            save_mps(pending, tensors)
            os.replace(pending, output)

        tensors, history = optimize(request, checkpoint=checkpoint)
        checkpoint(tensors)
        print(json.dumps({"trajectory": history, "wall_guard_fired": False}, allow_nan=False))
    except WallDeadlineReached:
        print(json.dumps({"wall_guard_fired": True, "valid_atomic_checkpoint_preserved": True}))
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0.0)


if __name__ == "__main__":
    main()
