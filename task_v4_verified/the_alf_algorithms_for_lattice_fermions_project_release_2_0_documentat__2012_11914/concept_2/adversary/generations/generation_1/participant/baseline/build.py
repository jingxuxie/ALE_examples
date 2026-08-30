import argparse
import json
from pathlib import Path


def baseline():
    order = ["X0", "X1", "Y0", "Y1", "V"]
    stages = []
    for substep in range(4):
        for position, component in enumerate(order + order[-2::-1]):
            coefficient = 0.25 if position == 4 else 0.125
            if stages and stages[-1]["component"] == component:
                stages[-1]["coefficient"] += coefficient
            else:
                stages.append({"component": component, "coefficient": coefficient})
    return {"schema_version": 1, "stages": stages}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=Path("OUTPUT/submission.json"))
    arguments = parser.parse_args()
    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    arguments.output.write_text(json.dumps(baseline(), indent=2) + "\n", encoding="utf-8")
    print(arguments.output)


if __name__ == "__main__":
    main()
