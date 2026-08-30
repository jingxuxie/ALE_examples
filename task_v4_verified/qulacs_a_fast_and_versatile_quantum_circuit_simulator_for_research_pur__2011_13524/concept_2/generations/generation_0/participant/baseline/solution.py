import json
import sys
from pathlib import Path


def main():
    if len(sys.argv) != 3:
        raise SystemExit("usage: python solution.py INPUT_JSON OUTPUT_JSON")
    specification = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    answer = {target["id"]: [] for target in specification["targets"]}
    Path(sys.argv[2]).write_text(
        json.dumps(answer, indent=2, allow_nan=False) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    main()
