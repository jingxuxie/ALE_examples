import json
import sys

from kernel import read_json, score_payload


if __name__ == "__main__":
    report = score_payload(read_json(sys.argv[1]), read_json(sys.argv[2]))
    print(json.dumps(report, indent=2, allow_nan=False))
