import argparse
import json
from pathlib import Path
import tempfile

import pipeline


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--seconds-per-case", type=float, default=300)
    arguments = parser.parse_args()
    if not 0 < arguments.seconds_per_case <= 3600:
        parser.error("seconds-per-case must be positive and at most 3600")
    source = arguments.input.resolve()
    destination = arguments.output.resolve()
    destination.parent.mkdir(parents=True, exist_ok=True)
    answer = {"cases": []}
    for instance in json.loads(source.read_text())["instances"]:
        if Path(instance["id"]).name != instance["id"]:
            raise ValueError("invalid identifier")
        with tempfile.TemporaryDirectory(prefix="champion2_", dir=destination.parent) as directory:
            answer["cases"].append(pipeline.recover(instance, arguments.seconds_per_case, source, Path(directory)))
        destination.write_text(json.dumps(answer, indent=2, allow_nan=False) + "\n")
    print(json.dumps({"completed_cases": len(answer["cases"])}))


if __name__ == "__main__":
    main()
