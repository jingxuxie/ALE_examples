import json
import sys

from contraction import baseline_plan


if __name__ == "__main__":
    print(json.dumps(baseline_plan(json.load(sys.stdin))))
