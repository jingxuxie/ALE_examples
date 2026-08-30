import argparse
from concurrent.futures import ThreadPoolExecutor
import json
import os
from pathlib import Path
import subprocess
import sys
import time


ROOT = Path(__file__).resolve().parents[2]


def run_one(case_path, kind, seconds):
    name = case_path.stem
    output_dir = ROOT / "attempts" / kind
    output_dir.mkdir(exist_ok=True)
    output = output_dir / (name + ".npz")
    command = [sys.executable]
    if kind == "baseline":
        command += [str(ROOT / "participant/baseline/solve.py")]
    else:
        command += [str(ROOT / "champions/portfolio.py"), "--seconds", str(seconds), "--history", str(output_dir / (name + "_history.json"))]
        if kind == "multistart":
            command += ["--mode", "multistart"]
        if kind == "expensive":
            command += ["--seed", "271828"]
    command += ["--input", str(case_path), "--output", str(output)]
    environment = dict(os.environ, OPENBLAS_NUM_THREADS="1", OMP_NUM_THREADS="1", MKL_NUM_THREADS="1", NUMEXPR_NUM_THREADS="1")
    started = time.monotonic()
    result = subprocess.run(command, capture_output=True, text=True, env=environment, timeout=max(seconds + 15, 90))
    record = {"case_id": name, "kind": kind, "elapsed_seconds": time.monotonic() - started, "returncode": result.returncode, "stdout": result.stdout, "stderr": result.stderr, "command": command, "timing_kind": "trusted builder process wall time, not sandbox qualification"}
    (output_dir / (name + ".json")).write_text(json.dumps(record, indent=2) + "\n")
    print(json.dumps(record), flush=True)
    return record


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--kind", choices=["baseline", "multistart", "portfolio", "expensive"], required=True)
    parser.add_argument("--seconds", type=float, default=54)
    parser.add_argument("--workers", type=int, default=3)
    parser.add_argument("--development", action="store_true")
    args = parser.parse_args()
    directory = ROOT / ("participant/input/cases" if args.development else "evaluator/hidden/cases")
    paths = sorted(directory.glob("*.json"))
    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        list(executor.map(lambda path: run_one(path, args.kind, args.seconds), paths))


if __name__ == "__main__":
    main()
