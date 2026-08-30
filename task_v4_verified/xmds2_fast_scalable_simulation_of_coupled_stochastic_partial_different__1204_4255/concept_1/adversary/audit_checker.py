import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import random
import sys
import time

sys.dont_write_bytecode = True
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "participant" / "workspace"))
from model import check
from privileged_planner import Planner, load_baseline


def tiny_instance(requests=None, capacity=4):
    return {"dimensions": 3, "sizes": [2, 1], "capacity": capacity,
            "axis_cost": [[[7 + layout + axis + direction for direction in range(2)] for axis in range(3)] for layout in range(3)],
            "transpose_cost": [[0 if source == destination else 13 + source + 2 * destination for destination in range(3)] for source in range(3)],
            "requests": requests if requests is not None else [{"field": 0, "mask": 2, "layout": 0, "updates": []}]}


def independent_semantics(instance, answer):
    dimensions = instance["dimensions"]
    generator = np.random.RandomState(82271)
    shape = tuple(2 + axis % 2 for axis in range(dimensions))
    homes = [generator.randn(*shape) + 1j * generator.randn(*shape) for size in instance["sizes"]]
    stored = {}
    position = 0
    cost = 0
    peak = 0
    maximum_error = 0.0

    def order(layout):
        return tuple([layout] + [axis for axis in range(dimensions) if axis != layout])

    def canonical(key):
        field, mask, layout = key
        if mask == 0 and layout == 0:
            return homes[field].copy()
        return np.transpose(stored[key], np.argsort(order(layout)))

    for action in answer["actions"]:
        kind = action[0]
        if kind == "read":
            request = instance["requests"][position]
            field = request["field"]
            key = (field, request["mask"], request["layout"])
            expected = homes[field].copy()
            for axis in range(dimensions):
                if request["mask"] & (1 << axis):
                    expected = np.fft.fft(expected, axis=axis)
            error = float(np.max(np.abs(expected - canonical(key))))
            maximum_error = max(maximum_error, error)
            if not np.allclose(expected, canonical(key), rtol=1e-10, atol=1e-10):
                raise AssertionError("Independent Fourier representation mismatch")
            for updated in set(request["updates"]):
                homes[updated] = generator.randn(*shape) + 1j * generator.randn(*shape)
                stored = {key: value for key, value in stored.items() if key[0] != updated}
            position += 1
        elif kind == "drop":
            del stored[tuple(action[1:])]
        else:
            field, mask, layout, coordinate, keep = action[1:]
            source = (field, mask, layout)
            value = canonical(source)
            if kind == "axis":
                previous_bit = (mask >> coordinate) & 1
                value = (np.fft.ifft if previous_bit else np.fft.fft)(value, axis=coordinate)
                destination = (field, mask ^ (1 << coordinate), layout)
                cost += instance["sizes"][field] * instance["axis_cost"][layout][coordinate][previous_bit]
            else:
                destination = (field, mask, coordinate)
                cost += instance["sizes"][field] * instance["transpose_cost"][layout][coordinate]
            if destination[1:] == (0, 0) or destination in stored:
                raise AssertionError("Invalid independent destination")
            if not keep:
                del stored[source]
            stored[destination] = np.transpose(value, order(destination[2])).copy()
        memory = sum(instance["sizes"][field] for field, mask, layout in stored)
        peak = max(peak, memory)
        if memory > instance["capacity"]:
            raise AssertionError("Independent scratch overflow")
    if position != len(instance["requests"]):
        raise AssertionError("Independent missing reads")
    return {"cost": cost, "peak_memory": peak, "reads": position, "max_fourier_error": maximum_error}


def main():
    started = time.perf_counter()
    cases = []
    base = tiny_instance()
    valid = [["axis", 0, 0, 0, 1, True], ["read"]]

    def test(name, actions, instance=None, accepted=False, answer=None):
        payload = {"actions": actions} if answer is None else answer
        try:
            result = check(instance or base, payload)
            outcome = {"name": name, "accepted": True, "result": result}
        except (ValueError, TypeError, IndexError, KeyError, OverflowError) as error:
            outcome = {"name": name, "accepted": False, "exception": type(error).__name__, "message": str(error)}
        outcome["expected_accepted"] = accepted
        outcome["passed"] = outcome["accepted"] == accepted
        cases.append(outcome)

    test("valid_basic", valid, accepted=True)
    test("empty_actions", [])
    test("read_without_representation", [["read"]])
    test("missing_final_read", valid[:-1])
    test("extra_read", valid + [["read"]])
    test("unknown_action", [["noop"]] + valid)
    test("empty_action", [[]] + valid)
    test("action_not_list", ["read"])
    test("action_kind_not_string", [[1]])
    test("too_many_actions", [["read"]] * 100001)
    test("actions_not_list", None, answer={"actions": {}})
    test("answer_extra_key", None, answer={"actions": valid, "cost": 0})
    test("answer_missing_key", None, answer={})
    test("answer_not_object", None, answer=[])
    test("read_arguments", valid[:-1] + [["read", 0]])
    test("axis_short", [["axis", 0, 0, 0, 1]])
    test("axis_long", [["axis", 0, 0, 0, 1, True, 0]])
    for index, coordinate in [(1, True), (1, 0.0), (1, -1), (1, 2), (2, True), (2, 8), (2, -1), (3, False), (3, 3), (3, -1), (4, True), (4, 1.0), (4, -1), (4, 3), (5, 1), (5, 0), (5, "true"), (5, None)]:
        action = valid[0].copy()
        action[index] = coordinate
        test("bad_coordinate_%s_%r" % (index, coordinate), [action, ["read"]])
    test("distributed_axis", [["axis", 0, 0, 0, 0, True]])
    test("transpose_same_layout", [["transpose", 0, 0, 0, 0, True]])
    test("drop_home", [["drop", 0, 0, 0]] + valid)
    test("overwrite_home_axis", [["axis", 0, 0, 0, 1, False], ["read"]])
    test("overwrite_home_transpose", [["transpose", 0, 0, 0, 1, False]])
    test("axis_destination_home", valid[:-1] + [["axis", 0, 2, 0, 1, False]])
    test("transpose_destination_home", [["transpose", 0, 0, 0, 1, True], ["transpose", 0, 0, 1, 0, False]])
    test("duplicate_destination", valid[:-1] + valid)
    test("drop_absent", [["drop", 0, 2, 0]] + valid)
    test("missing_source", [["axis", 0, 4, 0, 1, True]])
    test("capacity_checked_after_each_action", [["axis", 0, 0, 0, 1, True], ["axis", 0, 2, 0, 2, True], ["drop", 0, 2, 0]], instance=tiny_instance(capacity=2))
    in_place_instance = tiny_instance([{"field": 0, "mask": 6, "layout": 0, "updates": []}], capacity=2)
    test("in_place_single_buffer", [["axis", 0, 0, 0, 1, True], ["axis", 0, 2, 0, 2, False], ["read"]], instance=in_place_instance, accepted=True)
    test("memory_after_last_read", valid + [["axis", 0, 2, 0, 2, True]], instance=tiny_instance(capacity=2))
    test("post_read_cost_counted", valid + [["axis", 0, 2, 0, 2, False]], accepted=True)
    update_instance = tiny_instance([{"field": 0, "mask": 2, "layout": 0, "updates": [0]}, {"field": 0, "mask": 2, "layout": 0, "updates": []}])
    test("stale_read", valid + [["read"]], instance=update_instance)
    test("stale_transform_source", valid + [["axis", 0, 2, 0, 2, False], ["read"]], instance=update_instance)
    test("stale_drop", valid + [["drop", 0, 2, 0]], instance=update_instance)
    test("fresh_home_after_update", valid + valid, instance=update_instance, accepted=True)
    unaffected = tiny_instance([{"field": 0, "mask": 2, "layout": 0, "updates": [0]}, {"field": 1, "mask": 2, "layout": 0, "updates": []}])
    test("other_field_survives_update", [["axis", 1, 0, 0, 1, True]] + valid + [["read"]], instance=unaffected, accepted=True)
    test("home_outside_scratch", valid, instance=tiny_instance(capacity=2), accepted=True)
    rng = random.Random(220428)
    numerical = []
    baseline = load_baseline()
    for sample in range(50):
        requests = [{"field": rng.randrange(2), "mask": rng.randrange(8), "layout": rng.randrange(3), "updates": [rng.randrange(2)] if rng.random() < 0.18 else []} for position in range(30)]
        instance = tiny_instance(requests, capacity=rng.randrange(2, 7))
        for name, answer in [("baseline", baseline(instance)), ("weighted", Planner(instance).solve())]:
            exact = check(instance, answer)
            independent = independent_semantics(instance, answer)
            if any(exact[key] != independent[key] for key in ["cost", "peak_memory", "reads"]):
                raise AssertionError("Exact and independent simulators disagree")
            numerical.append({"sample": sample, "planner": name, **independent})
    evaluator_spec = importlib.util.spec_from_file_location("audited_evaluator", ROOT / "evaluator" / "evaluate.py")
    evaluator = importlib.util.module_from_spec(evaluator_spec)
    evaluator_spec.loader.exec_module(evaluator)
    boundary = []
    zero_instance = tiny_instance([{"field": 0, "mask": 0, "layout": 0, "updates": []} for position in range(30)])
    zero_path = HERE / "zero_cost_case.json"
    zero_path.write_text(json.dumps([{"id": "zero", "family": "zero", "instance": zero_instance, "baseline": {"cost": 0}}]))
    zero_answer = json.dumps({"actions": [["read"] for position in range(30)]}) + "\n"
    for name, text, path in [("zero_cost_protocol", zero_answer, zero_path), ("deep_json", "[" * 2000 + "0" + "]" * 2000 + "\n", zero_path)]:
        evaluator.run_submission = lambda *args, text=text, **kwargs: {"stdout": text, "returncode": 0, "timed_out": False, "elapsed_seconds": 0.01}
        try:
            result = evaluator.evaluate(HERE, path)
            boundary.append({"name": name, "result": result})
        except Exception as error:
            boundary.append({"name": name, "uncaught_exception": type(error).__name__, "message": str(error)})
    hashes = {}
    for name in ["participant/workspace/model.py", "participant/baseline/solve.py", "participant/input/protocol.md", "evaluator/evaluate.py", "evaluator/hidden/cases.json"]:
        hashes[name] = hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
    result = {"checker_cases": cases, "checker_tests_passed": sum(case["passed"] for case in cases), "checker_tests_total": len(cases), "numerical_runs": numerical, "numerical_read_count": sum(item["reads"] for item in numerical), "max_fourier_error": max(item["max_fourier_error"] for item in numerical), "evaluator_boundary": boundary, "hashes": hashes, "elapsed_seconds": time.perf_counter() - started}
    (HERE / "audit_results.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({key: value for key, value in result.items() if key not in ["checker_cases", "numerical_runs"]}, indent=2), flush=True)
    if not all(case["passed"] for case in cases):
        raise AssertionError("Checker expectation failed")


if __name__ == "__main__":
    main()
