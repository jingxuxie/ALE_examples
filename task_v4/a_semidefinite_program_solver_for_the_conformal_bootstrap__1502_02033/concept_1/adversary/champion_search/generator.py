import math

import numpy as np


SEED = 20260828
FAMILIES = ("dense_boundary", "pole_count_transition", "mixed_pole_models", "wide_damping",
            "three_scale_clusters", "correlated_uncertainty", "empty_poles_control", "remote_poles_control")


def validate(case):
    assert set(case) == {"degree", "scenarios"}
    assert type(case["degree"]) is int and 2 <= case["degree"] <= 48
    assert 2 <= len(case["scenarios"]) <= 6
    for scenario in case["scenarios"]:
        assert set(scenario) == {"a", "poles"}
        assert math.isfinite(scenario["a"]) and 0.02 <= scenario["a"] <= 5
        assert len(scenario["poles"]) <= 24
        assert all(math.isfinite(pole) and 1e-6 <= pole <= 10000 for pole in scenario["poles"])


def make_scenario(rate, poles):
    return {"a": float(np.clip(rate, 0.02, 5.0)),
            "poles": [float(np.clip(pole, 1e-6, 10000.0)) for pole in poles]}


def generate(rounds=16, seed=SEED):
    random = np.random.default_rng(seed)
    degrees = [4, 12, 24, 8, 36, 18, 48, 3, 22, 32, 6, 44, 2, 16, 28, 40]
    result = []
    for round_index in range(rounds):
        for family in FAMILIES:
            degree = degrees[round_index % len(degrees)]
            count = 2 + round_index % 5
            rate = float(10 ** random.uniform(-1.3, 0.35))
            uncertainty = np.linspace(-1, 1, count)
            scenarios = []
            if family == "dense_boundary":
                multiplicity = [24, 18, 24, 12, 24, 22, 24, 20][round_index % 8]
                pole = 10 ** random.uniform(-5.6, -1.4)
                for shift in uncertainty:
                    poles = [pole * math.exp(0.25 * shift)] * multiplicity
                    scenarios.append(make_scenario(rate * math.exp(0.12 * shift), poles))
            elif family == "pole_count_transition":
                degree = [2, 4, 8, 12, 18, 22, 24, 26][round_index % 8]
                pole = 10 ** random.uniform(-4.5, 0.1)
                for scenario_index, shift in enumerate(uncertainty):
                    multiplicity = min(24, max(1, degree - 2 + scenario_index))
                    scenarios.append(make_scenario(rate * math.exp(-0.08 * shift), [pole * math.exp(0.08 * shift)] * multiplicity))
            elif family == "mixed_pole_models":
                pole = 10 ** random.uniform(-1.7, 1.0)
                for scenario_index, shift in enumerate(uncertainty):
                    multiplicity = int(round(24 * scenario_index / (count - 1)))
                    poles = [pole] * (multiplicity // 2) + [pole * 5] * (multiplicity - multiplicity // 2)
                    scenarios.append(make_scenario(rate * math.exp(-0.45 * shift), poles))
            elif family == "wide_damping":
                ratio = [2, 4, 8, 16][round_index % 4]
                poles = [0.005, 0.00501, 0.2, 1, 5, 25]
                for shift in uncertainty:
                    scenarios.append(make_scenario(rate * ratio ** (shift / 2), poles))
            elif family == "three_scale_clusters":
                counts = [6, 12, 18, 24][round_index % 4]
                centers = [10 ** random.uniform(-5, -2), 10 ** random.uniform(-1.5, 0.5), 10 ** random.uniform(1.2, 3.2)]
                for shift in uncertainty:
                    poles = [centers[position % 3] * math.exp(shift * (0.6 if position % 3 == 0 else -0.25))
                             * (1 + 1e-5 * (position // 3)) for position in range(counts)]
                    scenarios.append(make_scenario(rate * math.exp(0.18 * shift), poles))
            elif family == "correlated_uncertainty":
                pole = 10 ** random.uniform(-3.5, 0.3)
                for scenario_index, shift in enumerate(uncertainty):
                    multiplicity = 4 + int(round(20 * scenario_index / (count - 1)))
                    poles = [pole * math.exp(2 * shift)] * multiplicity
                    scenarios.append(make_scenario(rate * math.exp(-0.7 * shift), poles))
            elif family == "empty_poles_control":
                for shift in uncertainty:
                    scenarios.append(make_scenario(rate * math.exp(0.15 * shift), []))
            else:
                pole = 10 ** random.uniform(1.5, 3.5)
                for shift in uncertainty:
                    poles = [pole * math.exp(0.4 * shift)] * (8 + round_index % 17)
                    scenarios.append(make_scenario(rate * math.exp(0.10 * shift), poles))
            case = {"degree": degree, "scenarios": scenarios}
            validate(case)
            result.append({"id": "%s_%02d" % (family, round_index), "family": family,
                           "seed": seed, "round": round_index, "input": case})
    return result
