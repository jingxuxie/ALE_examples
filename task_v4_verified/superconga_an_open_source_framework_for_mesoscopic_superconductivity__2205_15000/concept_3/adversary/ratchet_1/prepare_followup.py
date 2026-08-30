import argparse
import copy
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
sys.dont_write_bytecode = True


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--adapter-patch", action="store_true")
    parser.add_argument("--recheck", action="store_true")
    arguments = parser.parse_args()
    if arguments.adapter_patch:
        print("*** Begin Patch")
        for filename in ("solve.py", "inference.py", "physics.py"):
            source = (HERE / "submission" / filename).read_text()
            if filename == "solve.py":
                old = "physics.uniform_actions(56)[:44]"
                new = "physics.uniform_actions(56)[:max(4, model['query_budget'] - 12)]"
                if source.count(old) != 1:
                    raise ValueError("unexpected champion source")
                source = source.replace(old, new)
            destination = HERE / "frontier_submission" / filename
            if destination.exists():
                raise ValueError("frontier submission already staged")
            print("*** Add File: " + str(destination))
            print("\n".join("+" + line for line in source.splitlines()))
        print("*** End Patch")
        return
    cases = json.loads((HERE / "cases_96.json").read_text())["episodes"]
    if arguments.recheck:
        report_path = HERE / "screen_96" / "report.json"
        if report_path.exists():
            failed = set(json.loads(report_path.read_text())["failures"])
        else:
            completed = [json.loads(path.read_text()) for path in (HERE / "screen_96").glob("*.json")]
            failed = {result["case_id"] for result in completed if not result["metrics"]["joint_success"]}
        chosen = [case for case in cases if case["id"] in failed]
        if not chosen:
            chosen = sorted(cases, key=lambda case: json.loads((HERE / "screen_96" / (case["id"] + ".json")).read_text())["wall_seconds"], reverse=True)[:3]
        output = []
        for case in chosen:
            for repeat in range(2):
                copied = copy.deepcopy(case)
                copied["source_id"] = case["id"]
                copied["id"] = case["id"] + "-replay-" + str(repeat)
                output.append(copied)
        (HERE / "recheck_cases.json").write_text(json.dumps({"episodes": output}, indent=2) + "\n")
        print(json.dumps({"recheck_cases": len(output), "failures": len(failed)}))
    else:
        selection = [case for case in cases if case["cohort"] == "independent" and int(case["id"].rsplit("-", 1)[1]) < 8]
        (HERE / "frontier_cases_24.json").write_text(json.dumps({"episodes": selection, "selection": "first 8 preregistered independent draws per family, irrespective of outcomes"}, indent=2) + "\n")
        print(json.dumps({"frontier_cases": len(selection)}))


if __name__ == "__main__":
    main()
