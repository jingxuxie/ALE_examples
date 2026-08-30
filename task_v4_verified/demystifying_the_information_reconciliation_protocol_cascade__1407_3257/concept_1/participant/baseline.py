import argparse
import json
from pathlib import Path


def baseline_policy():
    schedule = []
    for basis, scale in [("paper_first", 1), ("paper_second", 1), ("frame", 0.25), ("frame", 0.5)]:
        schedule.append({"size": {"basis": basis, "scale": scale, "round": "nearest"},
                         "reuse": "all", "batch": "pass", "stop": False})
    return {"version": 1, "max_passes": 14, "schedule": schedule, "rules": []}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    arguments = parser.parse_args()
    Path(arguments.output).write_text(json.dumps(baseline_policy(), indent=2) + "\n")


if __name__ == "__main__":
    main()
