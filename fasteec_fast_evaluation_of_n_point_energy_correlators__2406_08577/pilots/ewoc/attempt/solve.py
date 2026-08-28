import argparse
import fcntl
import json
import math
import os
from pathlib import Path
import subprocess


ROOT = Path(__file__).resolve().parent
VENDOR = ROOT.parent / "participant" / "workspace" / "vendor"


def build_engine():
    source = ROOT / "engine.cc"
    binary = ROOT / "engine"
    library = VENDOR / "lib" / "libfastjet.a"
    with (ROOT / ".build.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        if binary.exists() and binary.stat().st_mtime_ns >= max(
            source.stat().st_mtime_ns, library.stat().st_mtime_ns
        ):
            return binary
        temporary = ROOT / ("engine.build." + str(os.getpid()))
        environment = os.environ.copy()
        environment["TMPDIR"] = str(ROOT)
        command = [
            "g++", "-std=c++17", "-O3", "-DNDEBUG",
            "-I" + str(VENDOR / "include"), str(source), str(library),
            "-lm", "-o", str(temporary),
        ]
        try:
            subprocess.run(command, check=True, cwd=ROOT, env=environment)
            os.replace(temporary, binary)
        finally:
            if temporary.exists():
                temporary.unlink()
    return binary


def encode_queries(job):
    nevents = int(job["nevents"])
    if nevents < 0:
        raise ValueError("nevents must be nonnegative")
    lines = [f"{nevents} {len(job['queries'])}"]
    for query in job["queries"]:
        geometry = {"pp": 0, "ee": 1}[query["geometry"]]
        algorithm = {"ca": 0, "kt": 1, "antikt": -1}[query["algorithm"]]
        observable = {"mass": 0, "angular": 1}[query["observable"]]
        radius = float(query["radius"])
        kappa = float(query["kappa"])
        log_min = float(query["log_min"])
        bins = int(query["bins"])
        log_upper = 4.0 if observable == 0 else math.log10(math.pi)
        if not (0.0 < radius <= math.pi and math.isfinite(kappa) and kappa > 0.0):
            raise ValueError("invalid radius or kappa")
        if not (math.isfinite(log_min) and log_min < log_upper and bins >= 3):
            raise ValueError("invalid histogram axis")
        lines.append(
            f"{geometry} {algorithm} {radius:.17g} {observable} "
            f"{kappa:.17g} {log_min:.17g} {bins}"
        )
    return "\n".join(lines) + "\n"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    arguments = parser.parse_args()
    job_path = Path(arguments.input).resolve()
    with job_path.open() as stream:
        job = json.load(stream)
    events_path = Path(job["events_file"])
    if not events_path.is_absolute():
        events_path = job_path.parent / events_path
    request = encode_queries(job)
    if job["queries"]:
        engine = build_engine()
        completed = subprocess.run(
            [str(engine), str(events_path)], input=request,
            text=True, stdout=subprocess.PIPE, check=True,
        )
        result = json.loads(completed.stdout)
    else:
        result = {"histograms": []}
    result["claims"] = {
        "method": (
            "Exact FastJet 3.4.3 E-scheme inclusive reclustering, with pp "
            "CA/kT/anti-kT or finite-radius ee generalized kT. Enumerates "
            "every diagonal once and every unordered off-diagonal twice, "
            "using original scalar-pt/energy denominators, post-clustering "
            "kappa weights, massive four-vectors, and explicit flow bins. "
            "Histograms are averaged over the supplied number of jets."
        ),
        "limitations": (
            "Double-precision floating-point roundoff at exactly degenerate "
            "clustering or bin boundaries; no sampling or multiplicity cuts."
        ),
    }
    with Path(arguments.output).open("w") as stream:
        json.dump(result, stream, allow_nan=False, separators=(",", ":"))
        stream.write("\n")


if __name__ == "__main__":
    main()
