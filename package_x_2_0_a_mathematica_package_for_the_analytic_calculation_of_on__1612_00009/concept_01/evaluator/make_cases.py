import copy
import itertools
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def matrix(count, entries):
    result = [[0.0] * count for index in range(count)]
    for (first, second), value in entries.items():
        result[first][second] = value
        result[second][first] = value
    return result


def integral(identifier, masses, invariants, **extras):
    return {"id": identifier, "masses2": masses, "invariants": invariants, "mu2": 1.7, **extras}


def make_suite(hidden):
    suffix = "holdout" if hidden else "release"
    cases = []
    entries = [-1.3, -2.2, -0.4, -1.6, -0.8, -2.7] if hidden else [-0.7, -1.1, -2.0, -0.4, -0.9, -0.6]
    invariant = matrix(4, dict(zip(itertools.combinations(range(4), 2), entries)))
    masses = [0.7, 1.8, 2.6, 1.1] if hidden else [1.0, 1.7, 0.8, 2.3]
    cases.append({"id": f"weighted_{suffix}", "family": "massive_weighted_tensor",
                  "integrals": [integral("weighted", masses, invariant, weights=[2, 1, 1, 2] if hidden else [1, 2, 1, 1],
                                         moments=[0, 1, 2, 0]),
                                integral("metric", masses, invariant, metric_pairs=1, dimension=6,
                                         weights=[1, 1, 2, 1], moments=[0, 2, 0, 1])]})
    first_channel = 11.0 if hidden else 7.5
    second_channel = -3.4 if hidden else -2.5
    invariant = matrix(4, {(0, 2): first_channel, (1, 3): second_channel})
    masses = [1.2, 0.8, 1.4, 0.9] if hidden else [1.0] * 4
    cases.append({"id": f"cut_{suffix}", "family": "massive_physical_cut",
                  "integrals": [integral("scalar", masses, invariant),
                                integral("metric", masses, invariant, metric_pairs=1),
                                integral("tensor", masses, invariant, moments=[0, 1, 0, 1])]})
    external = -1.8 if hidden else 3.2
    masses = [0.4, 2.7] if hidden else [1.3, 2.1]
    invariant = matrix(2, {(0, 1): external})
    terms = [{"integral": "metric", "epsilon_polynomial": [4, -2]},
             {"integral": "longitudinal", "epsilon_polynomial": [external]},
             {"integral": "pinch", "epsilon_polynomial": [-1]},
             {"integral": "scalar", "epsilon_polynomial": [-masses[0]]}]
    integrals = [integral("scalar", masses, invariant),
                 integral("metric", masses, invariant, metric_pairs=1),
                 integral("longitudinal", masses, invariant, moments=[0, 2]),
                 integral("pinch", [masses[1]], [[0]])]
    if hidden:
        integrals.append(integral("shifted_box", [0.6, 1.2, 0.9, 2.1],
                                  matrix(4, {(0, 2): -1.4, (1, 3): -0.8}), dimension=8))
    cases.append({"id": f"ultraviolet_{suffix}", "family": "uv_dimensional_trace", "integrals": integrals,
                  "observables": [{"id": "metric_trace", "terms": terms, "normalization": sum(masses), "expected_zero": True}]})
    channel = 7.1 if hidden else -3.4
    edge = (1, 2) if hidden else (0, 2)
    invariant = matrix(3, {edge: channel})
    moments_one = [0] * 3
    moments_two = [0] * 3
    moments_one[edge[0]] = 1
    moments_two[edge[0]] = moments_two[edge[1]] = 1
    direction = {"invariants": matrix(3, {edge: 0.7 if hidden else 1.0})}
    cases.append({"id": f"collinear_{suffix}", "family": "soft_collinear_triangle",
                  "integrals": [integral("scalar_jet", [0] * 3, invariant, directions=[direction], orders=[[0], [1], [2]]),
                                integral("single_pole", [0] * 3, invariant, moments=moments_one),
                                integral("finite_tensor", [0] * 3, invariant, moments=moments_two)]})
    invariant = matrix(4, {(0, 2): 6.5 if hidden else -4, (1, 3): -3.8 if hidden else -3, (0, 3): -2.4 if hidden else -1.3})
    cases.append({"id": f"massless_box_{suffix}", "family": "massless_box_infrared",
                  "integrals": [integral("one_mass", [0] * 4, invariant),
                                integral("on_shell", [0] * 4, matrix(4, {(0, 2): 8.0 if hidden else -5.0, (1, 3): -5 if hidden else -2.0}))]})
    points = [[0, 0], [0.6, 0.1], [-0.2, 0.7], [0.4, -0.5]] if hidden else [[0], [0.2], [-0.3], [0.7]]
    invariant = matrix(4, {(first, second): -sum((left - right) ** 2 for left, right in zip(points[first], points[second]))
                           for first, second in itertools.combinations(range(4), 2)})
    directions = [{"masses2": [0.1, -0.3, 0.2, 0.1]},
                  {"invariants": matrix(4, {(0, 2): -0.5, (1, 3): 0.2})}]
    orders = [list(order) for order in itertools.product(range(4), repeat=2) if sum(order) <= 3]
    primary = integral("mixed_jet", [0.3, 1.1, 0.8, 2.1] if hidden else [1, 1.00000001, 0.99999999, 1], invariant,
                       weights=[2, 1, 1, 1] if hidden else [1, 1, 2, 1], metric_pairs=1 if hidden else 0,
                       dimension=6 if hidden else 4, moments=[0, 1, 0, 2] if hidden else [0, 0, 0, 0],
                       directions=directions, orders=orders)
    rescaled = copy.deepcopy(primary)
    rescaled["id"] = "scaled_jet"
    factor = 1e-7 if hidden else 1e4
    rescaled["masses2"] = [value * factor for value in primary["masses2"]]
    rescaled["invariants"] = [[value * factor for value in row] for row in primary["invariants"]]
    rescaled["mu2"] *= factor
    for direction in rescaled["directions"]:
        if "masses2" in direction:
            direction["masses2"] = [value * factor for value in direction["masses2"]]
        if "invariants" in direction:
            direction["invariants"] = [[value * factor for value in row] for row in direction["invariants"]]
    cases.append({"id": f"matching_{suffix}", "family": "exceptional_gram_mixed_jets", "integrals": [primary, rescaled]})
    return {"schema": 1, "cases": cases}


def main():
    public = ROOT / "participant/v_01/input/release.json"
    private = ROOT / "evaluator/hidden/requests.json"
    public.write_text(json.dumps(make_suite(False), indent=2))
    private.write_text(json.dumps(make_suite(True), indent=2))


if __name__ == "__main__":
    main()
