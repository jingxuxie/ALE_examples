import contextlib
import importlib.util
import json
from pathlib import Path
import signal
import sys
import time


def limited(signum, frame):
    raise TimeoutError("stage allowance exhausted")


def replay(instance, seconds):
    import solve
    import search
    import refine
    import enumerate_supports
    modules = (solve, search, refine, enumerate_supports)
    for module in modules:
        module.ROOT = Path.cwd()
    path = Path.cwd() / (instance["id"] + ".json")
    signal.signal(signal.SIGALRM, limited)
    started = time.monotonic()
    stages = (
        (0.18, lambda: solve.Solver(instance).recover()),
        (0.24, lambda: search.search(instance)),
        (0.08, lambda: refine.refine(instance)),
        (0.50, lambda: enumerate_supports.enumerate_case(instance)),
    )
    with contextlib.redirect_stdout(sys.stderr):
        for fraction, stage in stages:
            if path.exists():
                case = json.loads(path.read_text())
                solver = solve.Solver(instance)
                error = solver.evaluate([atom["index"] for atom in case["atoms"]],
                                        solve.np.array([atom["ope"] for atom in case["atoms"]]))
                if error < 5e-9:
                    break
            remaining = seconds - (time.monotonic() - started)
            if remaining <= 0:
                break
            signal.setitimer(signal.ITIMER_REAL, min(remaining, seconds * fraction))
            try:
                stage()
            except Exception as error:
                print(type(error).__name__, str(error), file=sys.stderr, flush=True)
            finally:
                signal.setitimer(signal.ITIMER_REAL, 0)
    return json.loads(path.read_text()) if path.exists() else {"id": instance["id"], "atoms": []}


if __name__ == "__main__":
    payload = json.load(sys.stdin)
    result = replay(payload["instance"], float(payload.get("seconds", 60)))
    print(json.dumps(result), flush=True)
