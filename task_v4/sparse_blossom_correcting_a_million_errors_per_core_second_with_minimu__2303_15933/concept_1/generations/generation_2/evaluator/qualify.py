import argparse
import json
from pathlib import Path
import tempfile

from evaluate import ROOT, PARTICIPANT, np, read_predictions, run_isolated, sandbox_command, snapshot_submission


def execute(submission, shots=None, cpu_seconds=600):
    with tempfile.TemporaryDirectory(prefix="residual-qualify-") as directory:
        temporary = Path(directory)
        request_dir = temporary / "request"
        output_dir = temporary / "out"
        request_dir.mkdir()
        output_dir.mkdir()
        snapshot_submission(submission, temporary / "submission")
        items, expectations = [], {}
        for case_path in sorted((PARTICIPANT / "input/cases").iterdir()):
            case_id = case_path.name
            syndromes, baselines = [], []
            for split in ["challenge", "holdout"]:
                with np.load(ROOT / "evaluator/hidden" / split / (case_id + ".npz"), allow_pickle=False) as data:
                    syndromes.append(data["syndromes"] if shots is None else data["syndromes"][:shots])
                    baselines.append(data["baseline"] if shots is None else data["baseline"][:shots])
            np.savez_compressed(request_dir / (case_id + ".npz"), syndromes=np.concatenate(syndromes))
            expectations[case_id] = np.concatenate(baselines)
            items.append(dict(case_id=case_id, syndromes="/request/" + case_id + ".npz", predictions="/out/" + case_id + ".npz"))
        request = dict(submission="/submission/" + submission.name, participant_root="/participant", items=items,
            limits=dict(cpu_seconds=cpu_seconds, address_bytes=6 * 1024 ** 3))
        (request_dir / "request.json").write_text(json.dumps(request))
        execution = run_isolated(sandbox_command(PARTICIPANT, temporary / "submission", request_dir, output_dir), temporary / "worker.log", 900)
        report = dict(execution=execution, baseline_equal=False, valid=False, cases=[],
            worker_log=(temporary / "worker.log").read_text(errors="replace")[-10000:])
        if execution["returncode"] or execution["watchdog_timeout"]:
            return report
        try:
            for item in items:
                case_id = item["case_id"]
                expected = expectations[case_id]
                predicted = read_predictions(output_dir / (case_id + ".npz"), len(expected))
                report["cases"].append(dict(case_id=case_id, shots=len(expected),
                    baseline_disagreements=int(np.any(expected != predicted, axis=1).sum())))
            report["baseline_equal"] = all(case["baseline_disagreements"] == 0 for case in report["cases"])
            report["valid"] = True
        except Exception as error:
            report["error"] = f"{type(error).__name__}: {error}"
        return report


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--repetitions", type=int, default=2)
    parser.add_argument("--report", type=Path, default=ROOT / "evaluator/hidden/baseline_qualification.json")
    args = parser.parse_args()
    if args.report.exists():
        raise RuntimeError("Use a new report path; qualification is not silently overwritten")
    reports = []
    for repetition in range(args.repetitions):
        report = execute(PARTICIPANT / "baseline/submission.py")
        reports.append(report)
        print(json.dumps(dict(repetition=repetition, valid=report["valid"], baseline_equal=report["baseline_equal"], execution=report["execution"])), flush=True)
    result = dict(valid=all(report["valid"] and report["baseline_equal"] for report in reports), reports=reports,
        fresh_runner_launched=False, purpose="Trusted baseline CPU qualification before target freeze; not a fresh participant")
    args.report.write_text(json.dumps(result, indent=2) + "\n")
    return 0 if result["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
