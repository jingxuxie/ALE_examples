import json
import sys

sys.dont_write_bytecode = True
from privileged_planner import Planner, check, configurations, load_baseline


def main():
    baseline = load_baseline()
    for line in sys.stdin:
        if not line.strip():
            continue
        instance = json.loads(line)
        planner = Planner(instance)
        answer = baseline(instance)
        cost = check(instance, answer)["cost"]
        for config in configurations(1):
            candidate = planner.solve(**config)
            candidate_cost = check(instance, candidate)["cost"]
            if candidate_cost < cost:
                answer, cost = candidate, candidate_cost
        for scale in [1.5, 6.0]:
            candidate = planner.beam(width=32, local_width=4, scale=scale, source_count=2)
            candidate_cost = check(instance, candidate)["cost"]
            if candidate_cost < cost:
                answer, cost = candidate, candidate_cost
        print(json.dumps(answer, separators=(",", ":")), flush=True)


if __name__ == "__main__":
    main()
