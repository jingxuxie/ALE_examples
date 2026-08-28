import argparse
import json
import os
from pathlib import Path
import subprocess
import tempfile


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    root = Path(__file__).resolve().parent
    source = root / "engine.cpp"
    binary = root / "engine"
    if not binary.exists() or binary.stat().st_mtime_ns < source.stat().st_mtime_ns:
        vendor = root.parent / "participant" / "workspace" / "vendor"
        descriptor, temporary_path = tempfile.mkstemp(prefix="engine.build.", dir=root)
        os.close(descriptor)
        temporary = Path(temporary_path)
        command = [
            "g++", "-std=c++17", "-O3", "-DNDEBUG", "-march=native",
            "-I" + str(vendor / "include"), str(source),
            str(vendor / "lib" / "libfastjet.a"), "-lm", "-o", str(temporary),
        ]
        environment = dict(os.environ, TMPDIR=str(root))
        try:
            subprocess.run(command, check=True, cwd=root, env=environment)
            temporary.chmod(0o755)
            os.replace(temporary, binary)
        finally:
            temporary.unlink(missing_ok=True)
    job = json.loads(args.input.read_text())
    if job["kind"] != "weighted":
        raise ValueError("This engine implements the weighted contract.")
    events = (args.input.resolve().parent / job["events_file"]).resolve()
    lines = [str(events), str(job["nevents"]) + " " + str(len(job["queries"]))]
    for query in job["queries"]:
        lines.append(" ".join(str(value) for value in (
            query["order"], query["kappa"], query["algorithm"],
            query["resolution"], query["log_min"], query["bins"],
        )))
    completed = subprocess.run(
        [str(binary)], input="\n".join(lines) + "\n", text=True,
        stdout=subprocess.PIPE, check=True,
    )
    result = json.loads(completed.stdout)
    args.output.write_text(json.dumps(result, separators=(",", ":"), allow_nan=False))


if __name__ == "__main__":
    main()
