import argparse
import array
import json
import math
import os
from pathlib import Path
import subprocess
import tempfile


ROOT = Path(__file__).resolve().parent


def get_engine():
    source = ROOT / "engine.cpp"
    binary = ROOT / "engine"
    newest_source = max(source.stat().st_mtime_ns, Path(__file__).stat().st_mtime_ns)
    if not binary.exists() or binary.stat().st_mtime_ns < newest_source:
        temporary = ROOT / ("engine.build." + str(os.getpid()))
        try:
            subprocess.run(
                ["g++", "-std=c++17", "-O3", "-march=native", "-ffp-contract=fast",
                 "-DNDEBUG", "-DENGINE_VECTOR", str(source),
                 "-o", str(temporary), "-lmvec"],
                check=True,
            )
            os.replace(temporary, binary)
        finally:
            temporary.unlink(missing_ok=True)
    return binary


def compute(job, events_file, output_file):
    if job.get("kind", "resolved") != "resolved":
        raise ValueError("This engine implements the resolved contract.")
    nevents = int(job["nevents"])
    if nevents <= 0:
        raise ValueError("nevents must be positive")
    queries = job["queries"]
    configuration = [f"{nevents} {len(queries)}"]
    sizes = []
    for query in queries:
        order = int(query["order"])
        bins = int(query["bins"])
        ratio_bins = int(query["ratio_bins"])
        phi_bins = int(query["phi_bins"])
        log_min = float(query["log_min"])
        exponents = [float(query.get("nu1", 1)), float(query.get("nu2", 1)),
                     float(query.get("nu3", 1)) if order == 4 else 1.0]
        if order not in (3, 4) or bins < 3 or ratio_bins < 1 or phi_bins < 1:
            raise ValueError("Invalid order or bin count")
        if not math.isfinite(log_min) or log_min >= 0 or 10 ** log_min == 0:
            raise ValueError("Invalid logarithmic lower bound")
        if any(not math.isfinite(value) or value <= 0 for value in exponents):
            raise ValueError("Exponents must be finite and strictly positive")
        if not math.isfinite(1 + sum(exponents[:order - 1])):
            raise ValueError("Nonrepresentable total exponent")
        configuration.append(" ".join(map(str, [order, log_min, bins, ratio_bins,
                                                 phi_bins, *exponents])))
        sizes.append(bins * (ratio_bins * phi_bins) ** (order - 2))
    binary = get_engine()
    with tempfile.TemporaryDirectory(prefix="resolved-", dir=ROOT) as temporary:
        raw_output = Path(temporary) / "histograms.bin"
        subprocess.run(
            [str(binary), str(events_file), str(raw_output)],
            input="\n".join(configuration) + "\n", text=True, check=True,
        )
        with raw_output.open("rb") as stream, output_file.open("w") as destination:
            destination.write('{"histograms":[')
            for histogram_index, size in enumerate(sizes):
                if histogram_index:
                    destination.write(",")
                destination.write("[")
                remaining = size
                while remaining:
                    count = min(remaining, 65536)
                    values = array.array("d")
                    values.fromfile(stream, count)
                    if remaining != size:
                        destination.write(",")
                    encoded = json.dumps(values.tolist(), separators=(",", ":"), allow_nan=False)
                    destination.write(encoded[1:-1])
                    remaining -= count
                destination.write("]")
            destination.write('],"claims":')
            json.dump({
                "method": "Exact original-constituent radial ordering, phi-local finite "
                          "differences, and sparse conditional-cell factorization; inclusive "
                          "order-three contacts and contact-free recursive order four.",
                "limitations": "Double-precision arithmetic; non-unit weights have precisely "
                               "the source-defined binning dependence, not inclusive normalization. "
                               "No sampling, clustering, or multiplicity truncation is used.",
            }, destination, separators=(",", ":"))
            destination.write("}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    arguments = parser.parse_args()
    job = json.loads(arguments.input.read_text())
    events_file = Path(job["events_file"])
    if not events_file.is_absolute():
        events_file = arguments.input.resolve().parent / events_file
    compute(job, events_file, arguments.output)


if __name__ == "__main__":
    main()
