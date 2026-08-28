import argparse
import importlib.util
import json
import math
import os
import resource
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
specification = importlib.util.spec_from_file_location("private_reference", ROOT / "private/reference/solve.py")
reference = importlib.util.module_from_spec(specification)
specification.loader.exec_module(reference)


def limit_resources():
    resource.setrlimit(resource.RLIMIT_AS, (12 * 1024**3, 12 * 1024**3))


def score(value, truth, scale):
    if not isinstance(value, (int,float)) or not math.isfinite(value) or value < 0:
        return 0.0
    return 1 / (1 + ((value-truth)/scale)**2)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--solver", required=True)
    parser.add_argument("--split", default="pilot", choices=["pilot", "discovery", "heldout", "all"])
    parser.add_argument("--output", required=True)
    parser.add_argument("--stored-reference", action="store_true")
    parser.add_argument("--weak", action="store_true")
    parser.add_argument("--timeout", type=float, default=600)
    args = parser.parse_args()
    entries = json.loads((ROOT / "private/challenge_pool/cases.json").read_text())
    entries = [entry for entry in entries if args.split == "all" or entry["split"] == args.split]
    rows = []
    environment = dict(os.environ, OPENBLAS_NUM_THREADS="1", OMP_NUM_THREADS="1", MKL_NUM_THREADS="1")
    for entry in entries:
        started = time.monotonic()
        prediction = {}
        status = "ok"
        if args.stored_reference:
            prediction = dict(gap_meV=entry["gap_meV"], strength_meV=reference.strength(entry["case"]["mfp_nm"]))
        elif args.weak:
            prediction = dict(gap_meV=0.0, strength_meV=0.0)
        else:
            with tempfile.TemporaryDirectory(prefix="disorder-eval-") as temporary:
                input_path = Path(temporary) / "request.json"
                output_path = Path(temporary) / "result.json"
                input_path.write_text(json.dumps({"cases":[entry["case"]]}))
                command = [sys.executable, str(Path(args.solver).resolve()), "--input", str(input_path), "--output", str(output_path)]
                try:
                    process = subprocess.run(command, cwd=Path(args.solver).resolve().parent,
                                             env=environment, capture_output=True, text=True,
                                             timeout=args.timeout, preexec_fn=limit_resources)
                    if process.returncode:
                        status = f"exit {process.returncode}: {process.stderr[-2000:]}"
                    else:
                        result = json.loads(output_path.read_text())["results"]
                        prediction = next(item for item in result if item["id"] == entry["case"]["id"])
                except (subprocess.TimeoutExpired, OSError, ValueError, KeyError, StopIteration) as error:
                    status = f"{type(error).__name__}: {str(error)[-500:]}"
        gap_scale = max(0.20*entry["gap_meV"], 0.001)
        strength = reference.strength(entry["case"]["mfp_nm"])
        gap_score = score(prediction.get("gap_meV"), entry["gap_meV"], gap_scale)
        calibration_score = score(prediction.get("strength_meV"), strength, 0.02*strength)
        raw = 0.85*gap_score+0.15*calibration_score
        weak = 0.85*score(0, entry["gap_meV"], gap_scale)+0.15*score(0, strength, 0.02*strength)
        normalized = max(0.0, (raw-weak)/(1-weak))
        rows.append(dict(id=entry["case"]["id"], family=entry["family"], score=normalized,
                         gap_score=gap_score, calibration_score=calibration_score,
                         expected_gap=entry["gap_meV"], prediction=prediction,
                         runtime_seconds=time.monotonic()-started, status=status))
        print(json.dumps(rows[-1]), flush=True)
    families = {family: float(np.mean([row["score"] for row in rows if row["family"] == family]))
                for family in sorted({row["family"] for row in rows})}
    report = dict(core_score=float(np.mean([row["score"] for row in rows])),
                  worst_family=min(families.values()), families=families,
                  runtime_seconds=sum(row["runtime_seconds"] for row in rows), cases=rows,
                  reference_mode="archived author computation" if args.stored_reference else "executable submission")
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    Path(args.output).write_text(json.dumps(report, indent=2, allow_nan=False)+"\n")
    print(json.dumps({key:value for key,value in report.items() if key != "cases"}), flush=True)


if __name__ == "__main__":
    main()
