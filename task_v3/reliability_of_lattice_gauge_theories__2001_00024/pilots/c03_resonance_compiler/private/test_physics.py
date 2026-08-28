import copy
import itertools
import math
import unittest

import numpy as np

from case_factory import FAMILIES, make_case
from physics import compile_case
from scoring import evaluate_controls, matrix_for, relative_score, score_answer
from synthesis import weak_controls


def explicit_hilbert(case, channel, anchor):
    length = case["length"]
    states = np.asarray(list(itertools.product((0, 1), repeat=2 * length)), dtype=int)
    matter, links = states[:, :length], 2 * states[:, length:] - 1
    if case["model"] == "u1":
        generators = (matter + (links + np.roll(links, 1, axis=1)) / 2) * ((-1) ** np.arange(length))
        protection = generators.copy()
    else:
        electric = links * np.roll(links, 1, axis=1)
        generators = (1 - 2 * matter) * electric
        protection = electric + 2 * np.asarray(case["target"]) * matter - np.asarray(case["target"])
    target_columns = np.flatnonzero(np.all(generators == np.asarray(case["target"]), axis=1))
    raising = np.outer([0, 1], [1, 0]).astype(complex)
    lowering = raising.T
    matrices = {"I": np.eye(2), "raise": raising, "lower": lowering,
                "x": raising + lowering, "y": -1j * (raising - lowering),
                "z": np.diag([-1, 1]), "n": np.diag([0, 1])}
    rotation = np.asarray([[-1, 1], [1, 1]]) / math.sqrt(2)
    operator = np.zeros((len(states), len(states)), dtype=complex)
    for term in channel["terms"]:
        factors = [matrices["I"] for index in range(2 * length)]
        for kind, offset, name in term["ops"]:
            index = (anchor + offset) % length + (length if kind == "l" else 0)
            local = matrices[name]
            if case["model"] == "z2" and kind == "l":
                local = rotation.conj().T @ local @ rotation
            factors[index] = local
        product = np.ones((1, 1), dtype=complex)
        for factor in factors:
            product = np.kron(product, factor)
        operator += complex(*term["amplitude"]) * product
    if not np.allclose(operator, operator.conj().T, atol=1e-12):
        raise AssertionError("non-Hermitian physical channel")
    rows = set()
    for initial in target_columns:
        for final in np.flatnonzero(np.abs(operator[:, initial]) > 1e-10):
            sector = np.rint(generators[final] - generators[initial]).astype(int)
            penalty = np.rint(protection[final] - protection[initial]).astype(int)
            if np.any(sector):
                rows.add((tuple((site, int(value)) for site, value in enumerate(sector) if value),
                          tuple((site, int(value)) for site, value in enumerate(penalty) if value)))
    return rows


def independent_margin(case, vector, schedule, digital):
    hardware = case["hardware"]
    center = sum(value * schedule["ticks"][site] / hardware["denominator"] for site, value in vector)
    radius = sum(abs(value) * hardware["uncertainty"][site] for site, value in vector)
    lower, upper = center - radius, center + radius
    if not digital:
        return (0 if lower <= 0 <= upper else min(abs(lower), abs(upper))) / hardware["bandwidth"]
    phase = math.pi * schedule["phase_tick"] / hardware["phase_denominator"]
    lower, upper = lower * phase, upper * phase
    if math.ceil(lower / (2 * math.pi)) <= math.floor(upper / (2 * math.pi)):
        return 0.0
    return min(abs(np.angle(np.exp(1j * lower))), abs(np.angle(np.exp(1j * upper)))) / math.pi


class PhysicsChecks(unittest.TestCase):
    def test_explicit_hilbert_and_gaps(self):
        for family in FAMILIES:
            for variant in range(3):
                with self.subTest(family=family, variant=variant):
                    case = make_case(family, 4, 102 + variant, variant, "tiny")
                    for channel in case["channels"]:
                        channel["anchors"] = list(range(4))
                    certificate = compile_case(case)
                    lookup = {(entry["channel"], entry["anchor"]): entry for entry in certificate}
                    independent_vectors = set()
                    for channel in case["channels"]:
                        for anchor in channel["anchors"]:
                            exact = explicit_hilbert(case, channel, anchor)
                            observed = {(tuple(map(tuple, row["sector"])), tuple(map(tuple, row["penalty"])))
                                        for row in lookup[(channel["id"], anchor)]["transfers"]}
                            self.assertEqual(exact, observed, (family, channel["id"], anchor))
                            for sector, vector in exact:
                                sign = -1 if vector and vector[0][1] < 0 else 1
                                independent_vectors.add(tuple((site, sign * value) for site, value in vector))
                    matrix = matrix_for(case, certificate)
                    controls = weak_controls(case)
                    for name in ("analog", "digital"):
                        margins = [independent_margin(case, vector, controls[name], name == "digital")
                                   for vector in independent_vectors]
                        scored = evaluate_controls(case, matrix, controls[name], name == "digital")
                        self.assertAlmostEqual(min(margins), scored["minimum_margin"], places=11)
                        self.assertAlmostEqual(sum(margins) / len(margins), scored["mean_margin"], places=11)

    def test_alias_and_independent_scoring(self):
        case = make_case("u1_local", 4, 14, 0, "alias")
        case["channels"] = [case["channels"][0]]
        case["channels"][0]["anchors"] = [0]
        case["hardware"].update(caps=[9] * 4, phase_ticks=[12], uncertainty=[0] * 4)
        certificate = compile_case(case)
        matrix = matrix_for(case, certificate)
        controls = {"ticks": [9, -9, 9, -9], "phase_tick": 12}
        self.assertGreater(evaluate_controls(case, matrix, controls)["minimum_margin"], 1)
        self.assertAlmostEqual(evaluate_controls(case, matrix, controls, True)["minimum_margin"], 0)
        anchors = {name: {"weak": 0, "strong": 1} for name in ("analog", "digital")}
        answer = {"certificate": certificate, "analog": controls, "digital": controls}
        good = score_answer(case, certificate, answer, anchors)
        answer["certificate"] = []
        bad = score_answer(case, certificate, answer, anchors)
        self.assertEqual(good["analog"], bad["analog"])
        self.assertEqual(good["digital"], bad["digital"])
        self.assertEqual(bad["algebra"], 0)

    def test_pseudogenerator_not_generator(self):
        case = make_case("z2_pseudogenerator", 4, 18, 0, "pseudo")
        certificate = compile_case(case)
        self.assertTrue(any(row["sector"] != row["penalty"] for entry in certificate for row in entry["transfers"]))
        altered = copy.deepcopy(certificate)
        for entry in altered:
            for row in entry["transfers"]:
                row["penalty"] = row["sector"]
        answer = {"certificate": altered, **weak_controls(case)}
        anchors = {name: {"weak": 0, "strong": 1} for name in ("analog", "digital")}
        score = score_answer(case, certificate, answer, anchors)
        self.assertEqual(score["sector_f1"], 1)
        self.assertLess(score["transfer_f1"], 1)

    def test_calibration_and_hardware(self):
        self.assertAlmostEqual(relative_score(0, 0, 1), 0.05)
        self.assertAlmostEqual(relative_score(1, 0, 1), 0.95)
        self.assertGreater(relative_score(2, 0, 1), relative_score(1, 0, 1))
        self.assertLess(relative_score(2, 0, 1), relative_score(3, 0, 1))
        case = make_case("u1_local", 4, 14, 0, "bad")
        matrix = matrix_for(case, compile_case(case))
        for ticks in ([True] * 4, [99] * 4, [0.0] * 4, [0] * 3):
            with self.assertRaises(ValueError):
                evaluate_controls(case, matrix, {"ticks": ticks})


if __name__ == "__main__":
    unittest.main()
