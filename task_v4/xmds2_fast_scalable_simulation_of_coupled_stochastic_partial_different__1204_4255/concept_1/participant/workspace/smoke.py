import argparse
import json
from pathlib import Path
import subprocess
import sys

from model import check


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("solver")
    arguments = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    instances = [json.loads(line) for line in (root / "input" / "examples.jsonl").read_text().splitlines()]
    process = subprocess.run([sys.executable, arguments.solver], input="".join(json.dumps(instance) + "\n" for instance in instances), capture_output=True, text=True, timeout=120)
    answers = process.stdout.splitlines()
    if process.returncode or len(answers) != len(instances):
        raise RuntimeError(process.stderr or "wrong number of answers")
    for index, (instance, answer) in enumerate(zip(instances, answers)):
        result = check(instance, json.loads(answer))
        print(json.dumps({"example": index, **result}))


if __name__ == "__main__":
    main()
