import argparse
import hashlib
import importlib.util
import json
import os
import subprocess
import sys
import time
from pathlib import Path

import numpy as np
from scipy.optimize import minimize

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
import optimizer_copy as opt


def dump(name, value):
    (HERE / name).write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")


def fingerprint():
    names = ["evaluator/evaluate.py", "evaluator/hidden/field_control.py", "evaluator/hidden/protocol.json", "evaluator/hidden/cases.json", "participant/input/protocol.json"]
    return {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in names}


def summarize(scores, cases):
    return opt.fc.summarize(np.asarray(scores), cases, opt.PROTOCOL)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--seconds", type=float, default=1000.0)
    parser.add_argument("--iterations", type=int, default=200)
    parser.add_argument("--risk", type=float, default=60.0)
    parser.add_argument("--scale", type=float, default=1.0)
    parser.add_argument("--boundary-weight", type=float, default=100000.0)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--nx", type=int, default=48)
    parser.add_argument("--input", default=str(ROOT / "champions/generation_1/control.json"))
    parser.add_argument("--tag", default="risk60")
    parser.add_argument("--check", action="store_true")
    arguments = parser.parse_args()
    os.chdir(HERE)
    started = time.monotonic()
    frozen = fingerprint()
    cases = opt.fc.read_json(ROOT / "evaluator/hidden/cases.json")
    counts = {family: sum(case["family"] == family for case in cases) for family in {case["family"] for case in cases}}
    training = [dict(case, weight=0.7 / len(cases) + 0.3 / (len(counts) * counts[case["family"]])) for case in cases]
    dump(arguments.tag + ".cases.json", training)
    vector = opt.load(arguments.input)
    opt.fc.validate_artifact(opt.artifact(vector), opt.PROTOCOL)
    provenance = {"role": "privileged_postdeadline_generation_only", "generation": 2, "fresh_success": False, "live_gen2_attempts_read": False, "source_control": arguments.input, "source_control_sha256": hashlib.sha256(Path(arguments.input).read_bytes()).hexdigest(), "completed_optimizer": "attempts/v_2/optimize.py", "completed_optimizer_sha256": hashlib.sha256((ROOT / "attempts/v_2/optimize.py").read_bytes()).hexdigest(), "frozen_sha256": frozen, "parameters": vars(arguments), "started_unix": time.time(), "case_count": len(cases), "family_counts": counts}
    dump(arguments.tag + ".provenance.json", provenance)
    objective = opt.ParallelObjective(training, (arguments.nx, arguments.nx // 2), 0.04, arguments.risk, arguments.workers, arguments.boundary_weight)
    initial_value, initial_gradient = objective(vector)
    print("INITIAL", initial_value, summarize(objective.scores, cases), "seconds", time.monotonic() - started, flush=True)
    if arguments.check:
        checks = []
        for index in [2, 21, 40, 63, 80, 98]:
            plus, minus = vector.copy(), vector.copy()
            plus[index] += 1e-5
            minus[index] -= 1e-5
            numeric = (objective(plus)[0] - objective(minus)[0]) / 2e-5
            checks.append({"index": index, "adjoint": float(initial_gradient[index]), "numeric": float(numeric), "absolute_difference": float(abs(initial_gradient[index] - numeric))})
        dump(arguments.tag + ".gradient_check.json", checks)
        print("GRADIENT_CHECK", checks, flush=True)
        for connection in objective.connections:
            connection.send(None)
        return
    bounds, constraints = opt.constraints()
    history = []
    best_loss = float(initial_value)
    initial_summary = summarize(objective.scores, cases)
    best_deficit = max(0.9905 - initial_summary["core_score"], 0.9855 - initial_summary["worst_family_score"], 0.9807 - initial_summary["worst_case_score"])
    opt.write(HERE / (arguments.tag + ".best_loss.json"), vector)
    opt.write(HERE / (arguments.tag + ".best_score.json"), vector)
    stop_reason = "iteration_limit"

    def callback(current):
        nonlocal best_loss, best_deficit
        value, gradient = objective(current)
        checkpoint = current.copy().reshape(6, 19)
        peak = np.max(np.hypot(checkpoint[2], checkpoint[3]))
        if peak > 2.8 - 1e-9:
            checkpoint[2:4] *= (2.8 - 1e-9) / peak
        checkpoint = checkpoint.ravel()
        valid = True
        reason = "valid_control"
        try:
            opt.fc.validate_artifact(opt.artifact(checkpoint), opt.PROTOCOL)
        except ValueError as error:
            valid = False
            reason = str(error)
        scores = summarize(objective.scores, cases)
        deficit = max(0.9905 - scores["core_score"], 0.9855 - scores["worst_family_score"], 0.9807 - scores["worst_case_score"])
        record = dict(scores, iteration=len(history) + 1, calls=objective.calls, loss=float(value), deficit=float(deficit), valid=valid, reason=reason, seconds=time.monotonic() - started)
        history.append(record)
        if valid:
            opt.write(HERE / (arguments.tag + ".latest.json"), checkpoint)
            if value < best_loss:
                best_loss = value
                opt.write(HERE / (arguments.tag + ".best_loss.json"), checkpoint)
            if deficit < best_deficit:
                best_deficit = deficit
                opt.write(HERE / (arguments.tag + ".best_score.json"), checkpoint)
            if len(history) % 10 == 0:
                opt.write(HERE / (arguments.tag + ".iter%03d.json" % len(history)), checkpoint)
        dump(arguments.tag + ".history.json", history)
        print("ITER", json.dumps(record, allow_nan=False), flush=True)
        if valid and deficit < -0.0003:
            raise StopIteration("surrogate_margin_reached")
        if time.monotonic() - started >= arguments.seconds:
            raise StopIteration("search_time_limit")

    def scaled_objective(current):
        value, gradient = objective(current)
        return arguments.scale * value, arguments.scale * gradient

    try:
        result = minimize(scaled_objective, vector, jac=True, method="SLSQP", bounds=bounds, constraints=constraints, callback=callback, options={"maxiter": arguments.iterations, "ftol": 1e-10, "disp": True})
        stop_reason = str(result.message)
    except StopIteration as error:
        stop_reason = str(error)
    finally:
        for connection in objective.connections:
            connection.send(None)
        for process in objective.processes:
            process.join(timeout=10)
    assert frozen == fingerprint()
    dump(arguments.tag + ".completion.json", {"stop_reason": stop_reason, "seconds": time.monotonic() - started, "iterations": len(history), "best_surrogate_deficit": best_deficit, "best_loss": best_loss, "frozen_unchanged": True, "official_pass_claimed": False})
    print("COMPLETE", stop_reason, flush=True)


if __name__ == "__main__":
    main()
