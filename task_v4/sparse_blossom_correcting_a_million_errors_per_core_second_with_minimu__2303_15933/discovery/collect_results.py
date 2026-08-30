import argparse
import json
from pathlib import Path


def read_json(path):
    return json.loads(path.read_text()) if path.exists() else None


def collect_generation(generation, mode):
    status = read_json(generation / "status.json") or {}
    status = status.get("history_before_final_decision", status)
    baseline = status.get("champion_baseline", status.get("baseline"))
    if mode == "E":
        baseline = status.get("qualification", {}).get("weak", baseline)
        if baseline is None:
            for relative in ["attempts/baseline_report.json", "adversary/validation/weak_bounded_report.json",
                             "adversary/validation/weak_report.json"]:
                baseline = read_json(generation / relative)
                if baseline is not None:
                    break
    results = []
    for launch_path in sorted((generation / "attempts").glob("v_*_logs/launch.json")):
        if "stdin_infrastructure" in launch_path.parent.name:
            continue
        attempt = launch_path.parent.name.removesuffix("_logs")
        launch = read_json(launch_path)
        report_path = generation / "attempts" / (attempt + "_result.json")
        report = read_json(report_path) or {}
        result = {
            "attempt": attempt,
            "finished": "finished" in launch,
            "timed_out": launch.get("timed_out"),
            "coding_elapsed_seconds": launch.get("elapsed_seconds"),
            "report": str(report_path),
        }
        keys = ["valid", "passed", "core_score", "worst_family_score", "runtime_score",
                "reason", "mean_family_log_rmse", "worst_regime_family_log_rmse",
                "inherited_generation_two_score", "extension_score"]
        result.update({key: report[key] for key in keys if key in report})
        if mode == "A" and report:
            result["pooled"] = report.get("pooled")
            result["families"] = report.get("families")
            result["splits"] = report.get("splits")
            result["execution"] = report.get("execution")
        if mode == "B" and report:
            result["evaluation_cpu_seconds"] = report.get("evaluation_cpu_seconds")
            result["evaluation_seconds"] = report.get("evaluation_seconds")
        results.append(result)
    return {"path": str(generation), "mode": mode, "recorded_status": status.get("status"),
            "baseline": baseline, "fresh_attempts": results}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    generations = []
    for name, mode in [("concept_1", "A"), ("concept_2", "B"), ("concept_3", "E")]:
        concept = root / name
        generations.append(collect_generation(concept, mode))
        for generation in sorted((concept / "generations").glob("generation_*")):
            generations.append(collect_generation(generation, mode))
    result = {"paper": "2303.15933", "generation_count": len(generations),
              "generations": generations, "decisions_automatically_inferred": False}
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    for generation in generations:
        print(Path(generation["path"]).relative_to(root), generation["recorded_status"])
        for attempt in generation["fresh_attempts"]:
            print(" ", attempt["attempt"], "finished", attempt["finished"],
                  "passed", attempt.get("passed"), "core", attempt.get("core_score"),
                  "worst", attempt.get("worst_family_score"))


if __name__ == "__main__":
    main()
