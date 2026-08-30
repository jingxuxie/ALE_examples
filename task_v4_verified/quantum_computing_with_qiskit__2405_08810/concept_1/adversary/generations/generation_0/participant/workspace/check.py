import json
from pathlib import Path
import sys

from phase_model import check


def main():
    workloads = [json.loads(line) for line in Path(sys.argv[1]).read_text().splitlines() if line.strip()]
    circuits = [json.loads(line) for line in Path(sys.argv[2]).read_text().splitlines() if line.strip()]
    if len(workloads) != len(circuits):
        raise ValueError("one response is required for each workload")
    print(json.dumps([check(workload, circuit) for workload, circuit in zip(workloads, circuits)], indent=2))


if __name__ == "__main__":
    main()
