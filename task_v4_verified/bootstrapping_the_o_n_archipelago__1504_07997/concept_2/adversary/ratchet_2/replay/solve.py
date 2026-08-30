import argparse
import contextlib
import json
from pathlib import Path
import signal
import sys
import tempfile
import time

import champion_core
import enumerate_supports
import refine
import search


class StageTimeout(BaseException):
    pass


def expired(signum, frame):
    raise StageTimeout("stage time allowance exhausted")


def recover(instance, seconds, directory, input_path):
    for module in (champion_core, search, refine, enumerate_supports):
        module.ROOT = directory
        module.INPUT = input_path
    identifier = instance["id"]
    if Path(identifier).name != identifier:
        raise ValueError("case id must be a filename component")
    path = directory / (identifier + ".json")
    started = time.monotonic()
    signal.signal(signal.SIGALRM, expired)
    stages = (("recover", 0.18), ("search", 0.24), ("refine", 0.08), ("enumerate", 0.50))
    with contextlib.redirect_stdout(sys.stderr):
        for name, fraction in stages:
            if path.exists():
                previous = json.loads(path.read_text())
                solver = champion_core.Solver(instance)
                error = solver.evaluate([atom["index"] for atom in previous["atoms"]],
                                        champion_core.np.array([atom["ope"] for atom in previous["atoms"]]))
                if error < 5e-9:
                    break
            remaining = seconds - (time.monotonic() - started)
            if remaining <= 0:
                break
            allowance = remaining if name == "enumerate" else min(remaining, seconds * fraction)
            print("STAGE", name, "allowance", allowance, flush=True)
            signal.setitimer(signal.ITIMER_REAL, allowance)
            try:
                if name == "recover":
                    champion_core.Solver(instance).recover()
                elif name == "search":
                    search.search(instance)
                elif name == "refine":
                    refine.refine(instance)
                else:
                    enumerate_supports.enumerate_case(instance, allowance)
            except (Exception, StageTimeout) as error:
                print(type(error).__name__, str(error), flush=True)
            finally:
                signal.setitimer(signal.ITIMER_REAL, 0)
    return json.loads(path.read_text()) if path.exists() else {"id": identifier, "atoms": []}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--seconds-per-case", type=float, default=300)
    arguments = parser.parse_args()
    if not 0 < arguments.seconds_per_case <= 3600:
        parser.error("seconds-per-case must be in (0,3600]")
    source = arguments.input.resolve()
    destination = arguments.output.resolve()
    destination.parent.mkdir(parents=True, exist_ok=True)
    instances = json.loads(source.read_text())["instances"]
    answer = {"cases": []}
    for instance in instances:
        with tempfile.TemporaryDirectory(prefix="champion_work_", dir=destination.parent) as directory:
            answer["cases"].append(recover(instance, arguments.seconds_per_case, Path(directory), source))
        destination.write_text(json.dumps(answer, indent=2, allow_nan=False) + "\n")
    print(json.dumps({"completed_cases": len(answer["cases"])}))


if __name__ == "__main__":
    main()
