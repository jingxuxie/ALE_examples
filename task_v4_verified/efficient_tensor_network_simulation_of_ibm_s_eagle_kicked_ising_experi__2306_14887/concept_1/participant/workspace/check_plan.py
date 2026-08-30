import json
import sys

from contraction import assess


if __name__ == "__main__":
    with open(sys.argv[1]) as handle:
        instance = json.load(handle)
    with open(sys.argv[2]) as handle:
        plan = json.load(handle)
    metrics = assess(instance, plan)
    metrics.pop("frontiers")
    print(json.dumps(metrics, indent=2))
