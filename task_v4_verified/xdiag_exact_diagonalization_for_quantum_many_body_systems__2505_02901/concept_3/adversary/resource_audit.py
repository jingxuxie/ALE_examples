import argparse
import concurrent.futures
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "evaluator"))
import evaluate as checker
from evaluate import aggregate, evaluate_device


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--submission", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--jobs", type=int, default=4)
    parser.add_argument("--budgets", type=int, nargs="+", default=[6, 8, 12])
    parser.add_argument("--cases", type=Path, default=ROOT / "evaluator/hidden/devices.json")
    parser.add_argument("--package", type=Path, default=ROOT)
    arguments = parser.parse_args()
    checker.ROOT = arguments.package.resolve()
    original = json.loads((arguments.package / "participant/input/config.json").read_text())
    cases = json.loads(arguments.cases.read_text())
    total_shots = original["shots"] * original["query_budget"]
    submissions = arguments.submission.resolve()
    reports = {}
    for budget in arguments.budgets:
        assert total_shots % budget == 0
        config = dict(original, query_budget=budget, shots=total_shots // budget)
        with concurrent.futures.ThreadPoolExecutor(max_workers=arguments.jobs) as executor:
            results = list(executor.map(lambda case: evaluate_device(submissions, case, config), cases))
        report = aggregate(results, config)
        report["query_budget"] = budget
        report["shots_per_query"] = config["shots"]
        report["total_shots"] = total_shots
        reports[str(budget)] = report
        arguments.output.parent.mkdir(parents=True, exist_ok=True)
        arguments.output.write_text(json.dumps({"rationale": "Probe configurations have setup cost. Sweep their count at fixed total sampling budget to test experiment-design efficiency, not increased shot noise. These are prospective resource contracts, not changes to the original tournament grading.", "budgets": reports}, indent=2) + "\n")
        print(json.dumps({key: value for key, value in report.items() if key != "devices"}), flush=True)


if __name__ == "__main__":
    main()
