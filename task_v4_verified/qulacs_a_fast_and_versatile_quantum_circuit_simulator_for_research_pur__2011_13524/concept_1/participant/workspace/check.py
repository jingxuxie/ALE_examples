import json
import sys

from model import validate_and_cost


if __name__ == "__main__":
    cases = json.load(open(sys.argv[1]))["cases"]
    schedules = json.load(open(sys.argv[2]))["schedules"]
    costs = {case["id"]: validate_and_cost(case, schedules[case["id"]]) for case in cases}
    print(json.dumps({"valid": True, "costs": costs}, indent=2))
