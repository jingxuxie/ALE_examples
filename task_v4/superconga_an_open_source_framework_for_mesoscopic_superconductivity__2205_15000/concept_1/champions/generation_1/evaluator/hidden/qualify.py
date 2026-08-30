import argparse
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "evaluator"))
from evaluate import run_case
from independent import read_case, checked_field, energy_gradient


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--submission", type=Path, required=True)
    parser.add_argument("--name", required=True)
    parser.add_argument("--workers", type=int, default=6)
    args = parser.parse_args()
    target = read_case(ROOT / "evaluator/hidden/target.json")
    metadata = read_case(ROOT / "evaluator/hidden/generation.json")
    destination = ROOT / "attempts" / args.name
    destination.mkdir(exist_ok=True)

    def run(details):
        name = details["case_id"]
        case = read_case(ROOT / "evaluator/hidden/cases" / (name + ".json"))
        baseline_field = checked_field(ROOT / "attempts/baseline" / (name + ".npz"), case)
        baseline = energy_gradient(case, baseline_field)[0]
        reference = {"case_id": name, "family": details["family"], "case_path": "evaluator/hidden/cases/" + name + ".json", "baseline_energy": baseline, "witness_energy": baseline - 1}
        record = run_case(args.submission.resolve(), reference, target, capture_dir=destination)
        record["provisional_scores"] = "Ignore provisional gap scores: rescore captured fields after witness manifest freezes. Wall timing and checked energy are final."
        record["submission"] = str(args.submission.resolve())
        (destination / (name + ".json")).write_text(json.dumps(record, indent=2) + "\n")
        print(json.dumps(record), flush=True)

    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        list(executor.map(run, [details for details in metadata if not details["development"]]))


if __name__ == "__main__":
    main()
