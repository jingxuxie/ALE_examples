import contextlib
import json
import os
from pathlib import Path
import signal
import sys
import time

import continuous
import improve
import legacy_core
import seed


class StageTimeout(BaseException):
    pass


def expired(signum, frame):
    raise StageTimeout("stage allowance exhausted")


def recover(instance, seconds, source, directory):
    for module in (improve, seed, continuous):
        module.SOURCE = source
    improve.ROOT = directory
    os.environ["RESULT_DIR"] = "results"
    legacy_core.ROOT = directory / "legacy"
    legacy_core.ROOT.mkdir()
    legacy_core.INPUT = source
    signal.signal(signal.SIGALRM, expired)
    started = time.monotonic()
    stages = (("legacy_seed", min(5, seconds * 0.05)), ("whitened_seed", seconds * 0.15),
              ("discrete_improve", seconds * 0.15), ("continuous", seconds), ("final_improve", seconds))
    with contextlib.redirect_stdout(sys.stderr):
        for name, budget in stages:
            saved = improve.load_seed(instance["id"])
            if saved:
                solver = improve.Optimizer(instance)
                error = solver.evaluate([atom["index"] for atom in saved["atoms"]],
                                        improve.np.array([atom["ope"] for atom in saved["atoms"]]))
                if error < 1e-8:
                    break
            remaining = seconds - (time.monotonic() - started)
            if remaining <= 0:
                break
            allowance = min(budget, remaining)
            print("STAGE", name, "ALLOWANCE", allowance, flush=True)
            signal.setitimer(signal.ITIMER_REAL, allowance)
            try:
                if name == "legacy_seed":
                    legacy_core.Solver(instance).recover()
                elif name == "whitened_seed":
                    seed.recover(instance, allowance)
                elif name in ("discrete_improve", "final_improve"):
                    saved = improve.load_seed(instance["id"])
                    if saved:
                        improve.Optimizer(instance).improve(saved, allowance)
                else:
                    continuous.recover(instance, allowance)
            except (StageTimeout, Exception) as error:
                print("STAGE_ERROR", name, type(error).__name__, str(error), flush=True)
            finally:
                signal.setitimer(signal.ITIMER_REAL, 0)
    saved = improve.load_seed(instance["id"])
    return saved if saved else {"id": instance["id"], "atoms": [{"index": 0, "ope": [float(improve.np.sqrt(instance["shared_ope_squared"])), 0.0]}]}
