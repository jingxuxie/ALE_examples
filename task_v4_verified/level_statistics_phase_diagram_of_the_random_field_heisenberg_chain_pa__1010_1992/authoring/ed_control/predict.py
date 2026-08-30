import concurrent.futures
import json
import sys

from threadpoolctl import threadpool_limits

from physics import observables, sector


def calculate(case):
    with threadpool_limits(1):
        fraction = observables(case["fields"])["f"]
    return {"id": case["id"], "f": fraction}


if __name__ == "__main__":
    with threadpool_limits(1):
        sector(10)
        sector(12)
        with concurrent.futures.ProcessPoolExecutor(max_workers=4) as executor:
            print("READY", flush=True)
            payload = json.loads(sys.stdin.readline())
            predictions = list(executor.map(calculate, payload["cases"]))
            print(json.dumps({"predictions": predictions}), flush=True)
