import argparse
import ctypes
import os
from pathlib import Path
import resource
import subprocess
import sys
import tempfile
import time

os.environ["OMP_NUM_THREADS"] = "1"
os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"

import numpy as np


def cpu_seconds():
    return time.process_time() + resource.getrusage(resource.RUSAGE_CHILDREN).ru_utime + resource.getrusage(resource.RUSAGE_CHILDREN).ru_stime


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    with np.load(args.input, allow_pickle=False) as case:
        shape = tuple(int(value) for value in case["h_shape"])
        rows = np.ascontiguousarray(case["h_rows"], dtype=np.int32)
        columns = np.ascontiguousarray(case["h_cols"], dtype=np.int32)
        priors = np.ascontiguousarray(case["priors"], dtype=np.float64)
        syndromes = np.ascontiguousarray(case["syndromes"], dtype=np.uint8)
        budget = float(case["budget_seconds"]) if "budget_seconds" in case else 60.0
    checks, variables = shape
    if syndromes.ndim != 2 or syndromes.shape[1] != checks or priors.shape != (variables,):
        raise ValueError("Invalid input dimensions")
    if rows.shape != columns.shape or rows.ndim != 1:
        raise ValueError("Invalid sparse coordinates")
    if rows.size and (rows.min() < 0 or rows.max() >= checks or columns.min() < 0 or columns.max() >= variables):
        raise ValueError("Sparse coordinate outside matrix")
    if not np.all(np.isfinite(priors)) or np.any((priors < 0) | (priors > 1)):
        raise ValueError("Invalid fault probabilities")
    directory = Path(__file__).resolve().parent
    source = directory / "decoder.cpp"
    library = directory / "decoder_native.so"
    if not library.exists() or library.stat().st_mtime < source.stat().st_mtime:
        descriptor, temporary_name = tempfile.mkstemp(prefix="decoder_native.", suffix=".so", dir=directory)
        os.close(descriptor)
        temporary = Path(temporary_name)
        compiler_environment = dict(os.environ, TMPDIR=str(directory))
        subprocess.run(["g++", "-O3", "-mpopcnt", "-DNDEBUG", "-std=c++17", "-shared", "-fPIC", str(source), "-o", str(temporary)], check=True, cwd=directory, env=compiler_environment)
        temporary.chmod(0o755)
        os.replace(temporary, library)
    native = ctypes.CDLL(str(library))
    pointer = ctypes.c_void_p
    native.decode.argtypes = [ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int,
                              pointer, pointer, pointer, pointer, pointer, ctypes.c_double, pointer]
    native.decode.restype = ctypes.c_int
    corrections = np.zeros((syndromes.shape[0], variables), dtype=np.uint8)
    statistics = np.zeros(8, dtype=np.float64)
    remaining = max(0.05, budget - cpu_seconds() - 1.8)
    result = native.decode(checks, variables, len(rows), len(syndromes),
                           rows.ctypes.data, columns.ctypes.data, priors.ctypes.data,
                           syndromes.ctypes.data, corrections.ctypes.data,
                           remaining, statistics.ctypes.data)
    if result:
        raise RuntimeError("Native decoder failed: %d" % result)
    with open(args.output, "wb") as output:
        np.savez_compressed(output, corrections=corrections)
    if statistics[6]:
        print("Warning: %d syndrome rows are inconsistent with the supplied matrix." % int(statistics[6]), file=sys.stderr)
    if os.environ.get("DECODER_STATS"):
        print("decoder:", statistics.tolist(), "cpu:", cpu_seconds(), file=sys.stderr)


if __name__ == "__main__":
    main()
