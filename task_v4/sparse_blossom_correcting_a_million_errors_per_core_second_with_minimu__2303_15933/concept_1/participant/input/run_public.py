import argparse
import importlib.util
import json
from pathlib import Path
import sys
import time

PARTICIPANT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(PARTICIPANT / "input/runtime"), str(PARTICIPANT / "input"), str(PARTICIPANT)]

import numpy as np
from models import load_model


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--submission", type=Path, default=PARTICIPANT / "workspace/submission.py")
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    module_spec = importlib.util.spec_from_file_location("submission", args.submission.resolve())
    module = importlib.util.module_from_spec(module_spec)
    sys.path.insert(0, str(args.submission.resolve().parent))
    module_spec.loader.exec_module(module)
    results = []
    for path in sorted((PARTICIPANT / "input/calibration").glob("*.npz")):
        model = load_model(PARTICIPANT / "input/cases" / path.stem)
        with np.load(path, allow_pickle=False) as data:
            syndromes, labels, baseline = data["syndromes"], data["labels"], data["baseline"]
        started = time.process_time()
        predictions = module.Decoder(model).decode(syndromes)
        elapsed = time.process_time() - started
        if not isinstance(predictions, np.ndarray) or predictions.shape != labels.shape:
            raise ValueError("invalid prediction shape/type")
        if predictions.dtype.kind not in "biu" or not np.isin(predictions, [0, 1]).all():
            raise ValueError("nonbinary prediction")
        baseline_wrong = np.any(baseline != labels, axis=1)
        wrong = np.any(predictions != labels, axis=1)
        results.append(dict(case_id=path.stem, shots=len(labels), baseline_failures=int(baseline_wrong.sum()),
                            candidate_failures=int(wrong.sum()), corrected=int((baseline_wrong & ~wrong).sum()),
                            spoiled=int((~baseline_wrong & wrong).sum()), cpu_seconds=elapsed))
    baseline_count = sum(entry["baseline_failures"] for entry in results)
    failures = sum(entry["candidate_failures"] for entry in results)
    report = dict(kind="public_calibration_only", cases=results, baseline_failures=baseline_count,
                  candidate_failures=failures, error_reduction=1 - failures / baseline_count)
    text = json.dumps(report, indent=2) + "\n"
    if args.report:
        args.report.write_text(text)
    print(text)


if __name__ == "__main__":
    main()
