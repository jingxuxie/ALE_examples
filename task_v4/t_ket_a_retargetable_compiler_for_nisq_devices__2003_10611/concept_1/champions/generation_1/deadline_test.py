import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import time


def main():
    directory = Path(__file__).resolve().parent
    participant = directory.parents[1] / "participant"
    instance = json.loads((participant / "input/public_tree_1.json").read_text())
    sys.dont_write_bytecode = True
    spec = importlib.util.spec_from_file_location("validator", participant / "workspace/routing.py")
    validator = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(validator)
    bootstrap = 'import runpy,time; namespace=runpy.run_path("solve.py",run_name="test"); time.sleep(1); namespace["main"]()'
    started = time.monotonic()
    process = subprocess.run([sys.executable, "-c", bootstrap], input=json.dumps(instance),
                             text=True, capture_output=True, timeout=4,
                             env=dict(os.environ, ROUTE_TIME="1", ROUTE_DEBUG="1"))
    elapsed = time.monotonic() - started
    if process.returncode:
        raise RuntimeError(process.stderr)
    score = validator.validate(instance, json.loads(process.stdout))
    assert score["valid"] and "beams 0" in process.stderr, process.stderr
    print(json.dumps(dict(valid=True, injected_startup_delay=1, requested_budget=1,
                          seconds=elapsed, native_log=process.stderr.strip())))


if __name__ == "__main__":
    main()
