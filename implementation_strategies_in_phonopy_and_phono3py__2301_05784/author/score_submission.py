"""Common scoring entry point using each pilot's independent scientific metrics."""

import argparse
import importlib.util
import json
from pathlib import Path
import sys

from evaluation import evaluate, file_hash


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("concept", type=Path)
    parser.add_argument("submission", type=Path)
    parser.add_argument("--split", default="all")
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--participant", type=Path)
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--case", dest="case_ids", action="append")
    parser.add_argument("--stored-reference", action="store_true")
    args = parser.parse_args()
    evaluator_path = args.concept.resolve() / "private/evaluator.py"
    spec = importlib.util.spec_from_file_location("scientific_evaluator", evaluator_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)

    def score_components(actual, reference, baseline, case, input_data):
        result = module.score_case(actual, reference, baseline, case, input_data)
        if "fc2_branch" in result:
            return {
                f"fc{order}_branch": {
                    "score": result[f"fc{order}_branch"],
                    "error": result[f"raw_fc{order}_branch_error"],
                    "baseline_error": result[f"raw_fc{order}_baseline_branch_error"],
                    "raw_metrics": {key: value for key, value in result.items() if key.startswith("raw_")},
                }
                for order in (2, 3)
            }
        return result

    report = evaluate(args.concept, args.submission, args.split, args.report,
                      score_case=score_components, case_ids=args.case_ids,
                      stored_reference=args.stored_reference,
                      participant=args.participant, manifest_path=args.manifest)
    report["scientific_evaluator_sha256"] = file_hash(evaluator_path)
    report["score_definition"] = "Mean of two independent core-branch qualities, each 1/(1+error/weak_error_scale), with documented scientific floors. Raw errors and per-family minima retained; resource limits enforced separately."
    args.report.write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
    print(json.dumps(report["summary"], indent=2), flush=True)


if __name__ == "__main__":
    main()
