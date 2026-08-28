import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import subprocess
import tempfile


DIRECTORY = Path(__file__).resolve().parent
VENDOR = DIRECTORY.parent / "participant" / "workspace" / "vendor"


def executable():
    source = DIRECTORY / "correlator.cc"
    flags = ["-O3", "-std=c++17", "-DNDEBUG"]
    digest = hashlib.sha256(source.read_bytes() + " ".join(flags).encode()).hexdigest()[:16]
    binary = DIRECTORY / ("correlator_" + digest)
    if not binary.exists():
        with tempfile.TemporaryDirectory(prefix="build_", dir=DIRECTORY) as build_directory:
            temporary = Path(build_directory) / "engine"
            command = [
                "g++", *flags, str(source), "-I" + str(VENDOR / "include"),
                str(VENDOR / "lib" / "libfastjet.a"), "-lm", "-o", str(temporary),
            ]
            subprocess.run(command, check=True, cwd=build_directory,
                           env={**os.environ, "TMPDIR": build_directory})
            temporary.replace(binary)
    return binary


def compute(job, input_path, algorithm="cliques"):
    if job["kind"] != "fractional":
        raise ValueError("This submission implements the continuous-order fractional observable.")
    nevents = int(job["nevents"])
    if nevents <= 0:
        raise ValueError("nevents must be positive")
    rows = [str(len(job["queries"]))]
    for query in job["queries"]:
        nu = float(query["nu"])
        nsub = int(query["nsub"])
        log_min = float(query["log_min"])
        bins = int(query["bins"])
        if not (math.isfinite(nu) and nu > 0 and 2 <= nsub <= 16):
            raise ValueError("Invalid order or subjet resolution")
        if not (math.isfinite(log_min) and log_min < 0 and bins > 0):
            raise ValueError("Invalid histogram axis")
        rows.append(f"{nu:.17g} {nsub} {log_min:.17g} {bins}")
    events = (input_path.parent / job["events_file"]).resolve()
    result = subprocess.run(
        [str(executable()), str(events), str(nevents), algorithm],
        input="\n".join(rows) + "\n", text=True, capture_output=True, check=True,
        env={**os.environ, "OMP_NUM_THREADS": "1", "OPENBLAS_NUM_THREADS": "1"},
    )
    histograms = json.loads(result.stdout)
    if any(not math.isfinite(value) for histogram in histograms for value in histogram):
        raise ArithmeticError("Nonfinite histogram")
    return {
        "histograms": histograms,
        "claims": {
            "method": "Exact signed diameter-bin subset measure via maximal-clique inclusion-exclusion; FastJet C/A R=1.5 pt_scheme, independent per-child exclusive-subjet caps, and original-constituent contacts.",
            "limitations": "Floating-point arithmetic; implements the specified bounded-resolution fractional observable, not an uncompressed full-particle observable. No sampling, order interpolation, or histogram renormalization.",
        },
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    arguments = parser.parse_args()
    input_path = arguments.input.resolve()
    result = compute(json.loads(input_path.read_text()), input_path)
    arguments.output.write_text(json.dumps(result, allow_nan=False, separators=(",", ":")))


if __name__ == "__main__":
    main()
