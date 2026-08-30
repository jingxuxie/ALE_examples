import json
import sys
import time


hello = json.loads(sys.stdin.readline())
started = time.process_time()
counter = 0
while time.process_time() - started < 1.0:
    counter += 1
print(json.dumps({"type": "ready"}), flush=True)
targets = json.loads(sys.stdin.readline())["matchings"]
print(json.dumps({"type": "final", "predictions": [.05] * len(targets)}), flush=True)
json.loads(sys.stdin.readline())
print(json.dumps({"self_reported_process_cpu_seconds": time.process_time() - started,
                  "iterations": counter}), file=sys.stderr, flush=True)
