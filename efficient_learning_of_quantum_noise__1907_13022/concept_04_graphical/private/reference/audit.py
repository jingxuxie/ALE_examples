import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import time

import numpy as np

from author_tools import case, exhaustive, load_model, oracle
from solver import canonical_factors, fixed_cmi, learn, marginal, solve, solve_factors, tables_from_data
from weak_solver import independent_rates, solve as weak_solve


ROOT = Path(__file__).resolve().parents[2]
sys.dont_write_bytecode = True
specification = importlib.util.spec_from_file_location("graphical_evaluator", ROOT / "private/evaluator.py")
evaluator = importlib.util.module_from_spec(specification)
specification.loader.exec_module(evaluator)


def direct_marginal(probabilities, num_variables, axes):
    codes = np.arange(2 ** num_variables, dtype=np.int64)
    mapped = np.zeros(len(codes), dtype=np.int64)
    for position, axis in enumerate(axes):
        mapped += ((codes >> axis) & 1) << position
    return np.bincount(mapped, weights=probabilities, minlength=2 ** len(axes))


def entropy(probabilities):
    positive = probabilities[probabilities > 0]
    return float(-positive @ np.log2(positive))


def entropy_cmi(probabilities, num_variables, first, second, given):
    return (
        entropy(direct_marginal(probabilities, num_variables, first + given))
        + entropy(direct_marginal(probabilities, num_variables, second + given))
        - entropy(direct_marginal(probabilities, num_variables, given))
        - entropy(direct_marginal(probabilities, num_variables, first + second + given))
    )


def old_stride_cmi(table, first, second, given):
    xsize, ysize, zsize = 2 ** len(first), 2 ** len(second), 2 ** len(given)
    joint = marginal(table, first + second + given).reshape(xsize * ysize, zsize, order="F")
    first_joint = marginal(table, first + given).reshape(xsize, zsize, order="F")
    second_joint = marginal(table, second + given).reshape(ysize, zsize, order="F")
    given_joint = marginal(table, given).ravel(order="F")
    total = 0.0
    for first_value in range(xsize):
        for second_value in range(ysize):
            weights = joint[ysize * second_value + first_value]
            total += float(weights @ np.log2(weights * given_joint / first_joint[first_value] / second_joint[second_value]))
    return total


def cmi_checks():
    rng = np.random.default_rng(85341)
    probabilities = rng.uniform(0.01, 2.0, 64)
    probabilities /= probabilities.sum()
    table = probabilities.reshape((2,) * 6, order="F")
    groups = [((4,), (2, 0), (5, 1, 3)), ((1, 4), (2,), (0, 5)), ((5, 3), (1, 0, 4), (2,)), ((3,), (0, 5), ())]
    errors, old_failures = [], []
    for first, second, given in groups:
        expected = entropy_cmi(probabilities, 6, first, second, given)
        corrected = fixed_cmi(table, first, second, given)
        errors.append(abs(expected - corrected))
        try:
            broken = old_stride_cmi(table, first, second, given)
            old_failures.append({"kind": "wrong_value", "absolute_error": abs(expected - broken)})
            assert abs(expected - broken) > 1e-6
        except IndexError:
            old_failures.append({"kind": "index_error"})
    tiny, coefficients, order = case("mediated_chain", 8, 74016)
    answers, full = exhaustive(tiny, coefficients)
    chain_table = full.reshape((2,) * 8, order="F")
    first, mediator, second = order[:3]
    unconditioned = fixed_cmi(chain_table, (first,), (second,), ())
    conditioned = fixed_cmi(chain_table, (first,), (second,), (mediator,))
    assert unconditioned > 1e-10 and abs(conditioned) < 1e-12
    patterns = np.arange(8)
    parity = np.array([int(value).bit_count() % 2 for value in patterns])
    synergistic = np.exp(1.1 * (1 - 2 * parity))
    synergistic /= synergistic.sum()
    synergy_table = synergistic.reshape(2, 2, 2, order="F")
    synergy_pair = fixed_cmi(synergy_table, (0,), (1,), ())
    synergy_conditional = fixed_cmi(synergy_table, (0,), (1,), (2,))
    assert abs(synergy_pair) < 1e-12 and synergy_conditional > 0.1
    assert max(errors) < 2e-12
    return {"grouped_entropy_max_error": max(errors), "old_stride_failures": old_failures,
            "mediator_pair_mi_bits": unconditioned, "mediator_cmi_bits": conditioned,
            "synergy_pair_mi_bits": synergy_pair, "synergy_cmi_bits": synergy_conditional}


def small_checks():
    results = []
    for family, num_variables in (("mediated_chain", 10), ("loop_ladder", 10), ("branch_triples", 12)):
        for region in (0, 2):
            data, coefficients, order = case(family, num_variables, np.random.SeedSequence([95117, num_variables, region]), region)
            data["fixed"][12, order[:2]] = 1
            data["count_mask"][12] = 1
            data["weight_lo"][12] = 2
            data["weight_hi"][12] = num_variables - 2
            data["parity_mask"][12, order[:2]] = 1
            data["parity_mask"][12, order[2]] = 1
            brute, full = exhaustive(data, coefficients)
            contraction = oracle(data, coefficients, order)
            reconstructed = solve(data)
            marginal_error = 0.0
            for center, scope, table in tables_from_data(data):
                direct = direct_marginal(full, num_variables, scope)
                marginal_error = max(marginal_error, float(np.max(np.abs(direct - table.ravel(order="F")))))
            coefficients_learned = learn(data)
            keys = set(coefficients) | set(coefficients_learned)
            coefficient_error = max(abs(coefficients.get(scope, 0.0) - coefficients_learned.get(scope, 0.0)) for scope in keys)
            oracle_error = float(np.max(np.abs(brute - contraction)))
            reference_error = float(np.max(np.abs(brute - reconstructed)))
            assert marginal_error < 2e-12 and coefficient_error < 1e-8
            assert oracle_error < 2e-10 and reference_error < 2e-10
            results.append({"family": family, "n": num_variables, "region": region, "states_enumerated": 2 ** num_variables,
                            "marginal_max_error": marginal_error, "coefficient_max_error": coefficient_error,
                            "oracle_log_max_error": oracle_error, "reference_log_max_error": reference_error})
    return results


def output_checks():
    rejected = []
    with tempfile.TemporaryDirectory(dir=ROOT / "private/reference") as temporary:
        destination = Path(temporary) / "output.npz"
        np.savez(destination, log_event=np.array([-1.0, -900.0, -0.1], dtype=np.float64))
        assert np.array_equal(evaluator.read_prediction(destination, 3), [-1.0, -900.0, -0.1])
        variants = {
            "nonfinite": {"log_event": np.array([-1.0, np.nan, -2.0])},
            "positive": {"log_event": np.array([-1.0, 1.0, -2.0])},
            "wrong_length": {"log_event": np.array([-1.0])},
            "wrong_dtype": {"log_event": np.array([-1.0, -2.0, -3.0], dtype=np.float32)},
            "extra_array": {"log_event": np.array([-1.0, -2.0, -3.0]), "extra": np.zeros(1)},
            "pickle": {"log_event": np.array([{}, {}, {}], dtype=object)},
        }
        for name, content in variants.items():
            np.savez(destination, **content)
            try:
                evaluator.read_prediction(destination, 3)
            except ValueError:
                rejected.append(name)
            else:
                raise AssertionError(f"Accepted malformed output: {name}")
    return {"valid_log_underflow_accepted": True, "malformed_rejected": rejected}


def tree_factors(data):
    num_variables = int(data["n"])
    rates = independent_rates(data)
    single = {node: np.array([1 - rates[node], rates[node]]) for node in range(num_variables)}
    pairs = {}
    for center, scope, table in tables_from_data(data):
        for neighbor in scope:
            if neighbor == center:
                continue
            pair = tuple(sorted((center, neighbor)))
            pairs[pair] = marginal(table, tuple(scope.index(node) for node in pair))
    edges = []
    for pair, joint in pairs.items():
        product = single[pair[0]][:, None] * single[pair[1]][None, :]
        information = float(np.sum(joint * np.log(joint / product)))
        edges.append((information, pair, joint))
    parent = list(range(num_variables))

    def root(node):
        while parent[node] != node:
            parent[node] = parent[parent[node]]
            node = parent[node]
        return node

    factors = [((node,), np.log(single[node])) for node in range(num_variables)]
    for information, pair, joint in sorted(edges, key=lambda item: item[0], reverse=True):
        first, second = root(pair[0]), root(pair[1])
        if first == second:
            continue
        parent[first] = second
        values = np.log(joint) - np.log(single[pair[0]])[:, None] - np.log(single[pair[1]])[None, :]
        factors.append((pair, values))
    return factors


def pool_checks():
    manifest = json.loads((ROOT / "private/reference/manifest.json").read_text())
    results = []
    allowed_keys = {"version", "n", "max_order", "centers", "scope_nodes", "scope_size", "local_ptr", "local_probs",
                    "log_activity", "fixed", "count_mask", "weight_lo", "weight_hi", "parity_mask", "parity_value", "event_group"}
    for entry in manifest["cases"]:
        with np.load(ROOT / entry["input"], allow_pickle=False) as archive:
            data = dict(archive)
        with np.load(ROOT / entry["truth"], allow_pickle=False) as archive:
            target, baseline, groups = archive["target"], archive["baseline"], archive["event_group"]
        assert set(data) == allowed_keys
        assert all(int(data["weight_lo"][query]) > 0 or np.any(data["fixed"][query] == 1) or int(data["parity_value"][query]) == 1 for query in range(len(target)))
        coefficients, order = load_model(ROOT / entry["model"])
        strong = solve(data)
        assert np.max(np.abs(strong - target)) < 2e-8
        native = dict(data)
        native["log_activity"] = np.zeros_like(data["log_activity"])
        variants = {
            "independent": baseline,
            "pair_truncated": solve_factors(data, canonical_factors(learn(data, pair_only=True))),
            "pair_mi_tree": solve_factors(data, tree_factors(data)),
            "ignore_activity": solve_factors(native, canonical_factors(learn(data))),
            "float64_probability_floor": np.maximum(target, np.log(np.finfo(np.float64).tiny)),
            "constant_log_zero": np.zeros_like(target),
        }
        ablations = {name: evaluator.score(prediction, target, baseline, groups)[0] for name, prediction in variants.items()}
        progress = [evaluator.score(baseline + fraction * (target - baseline), target, baseline, groups)[0] for fraction in (0.0, 0.25, 0.5, 0.75, 0.9, 0.99, 1.0)]
        assert np.all(np.diff(progress) > 0)
        results.append({"id": entry["id"], "family": entry["family"], "pool": entry["pool"],
                        "reference_max_log_error": float(np.max(np.abs(strong - target))),
                        "below_normal_float64": int(np.sum(target < np.log(np.finfo(np.float64).tiny))),
                        "below_subnormal_float64": int(np.sum(target < np.log(np.nextafter(0.0, 1.0)))),
                        "ablations": ablations, "score_interpolation": progress})
        print(f"audited {entry['id']}: {ablations}", flush=True)
    summaries = {}
    for family in sorted({entry["family"] for entry in results}):
        selected = [entry for entry in results if entry["family"] == family]
        summaries[family] = {name: float(np.mean([entry["ablations"][name] for entry in selected])) for name in selected[0]["ablations"]}
    return {"cases": results, "families": summaries}


def ratchet_checks(seed):
    results = []
    for region in (1, 2):
        for family, num_variables in (("mediated_chain", 100), ("loop_ladder", 100), ("branch_triples", 102)):
            stream = np.random.SeedSequence([seed, region, num_variables, 192301])
            data, coefficients, order = case(family, num_variables, stream, region, True)
            target = oracle(data, coefficients, order)
            reconstructed = solve(data)
            baseline = weak_solve(data)
            error = float(np.max(np.abs(target - reconstructed)))
            value, grouped = evaluator.score(reconstructed, target, baseline, data["event_group"])
            assert error < 2e-8 and value > 0.9
            fingerprint = hashlib.sha256(data["local_probs"].tobytes() + data["scope_nodes"].tobytes() + data["fixed"].tobytes()).hexdigest()
            results.append({"family": family, "region": region, "n": num_variables, "seed": seed, "fingerprint": fingerprint,
                            "reference_score": value, "reference_max_log_error": error})
    assert len({entry["fingerprint"] for entry in results}) == len(results)
    return results


def main(output, seed):
    started = time.monotonic()
    report = {"cmi": cmi_checks(), "exhaustive": small_checks(), "output_validation": output_checks(), "pool": pool_checks(), "ratchet": ratchet_checks(seed)}
    report["runtime"] = time.monotonic() - started
    output.write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
    print(json.dumps({"status": "passed", "exhaustive_cases": len(report["exhaustive"]), "pool_cases": len(report["pool"]["cases"]), "fresh_ratchet_cases": len(report["ratchet"]), "runtime": report["runtime"]}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=Path(__file__).with_name("audit.json"))
    parser.add_argument("--seed", type=int, default=918273)
    arguments = parser.parse_args()
    main(arguments.output, arguments.seed)
