import hashlib
import json


def scenarios(rate, pole_sets, shifts):
    return [{"a": rate * shift, "poles": [float(pole / rate) for pole in poles]}
            for poles, shift in zip(pole_sets, shifts)]


def hidden_cases():
    cases = []
    for index, (degree, rate) in enumerate(((13, 0.23), (23, 1.9), (37, 0.71))):
        poles = [0.38, 1.4, 3.2, 7.0]
        cases.append({"id": "damping_" + str(index), "family": "damping_uncertainty", "degree": degree,
                      "scenarios": scenarios(rate, [poles, poles, poles, poles], [0.88, 0.97, 1.04, 1.13])})
    for index, (degree, rate, tiny) in enumerate(((15, 0.6, 0.0023), (25, 1.3, 0.00019), (35, 0.11, 0.009))):
        poles = [tiny, tiny, tiny * 1.003, 0.19, 0.7, 2.8]
        sets = [[pole * factor for pole in poles] for factor in (0.79, 1.0, 1.27)]
        cases.append({"id": "edge_" + str(index), "family": "near_origin_clusters", "degree": degree,
                      "scenarios": scenarios(rate, sets, [0.95, 1.02, 1.06])})
    for index, (degree, rate, cluster) in enumerate(((17, 2.1, 0.12), (29, 0.083, 0.047), (39, 0.93, 0.008))):
        poles = [cluster, cluster * 1.0002, 0.6, 0.61, 4.8, 4.81, 34.0, 130.0]
        sets = [poles, [pole * (1.19 if pos < 4 else 0.86) for pos, pole in enumerate(poles)],
                [pole * (0.87 if pos < 4 else 1.22) for pos, pole in enumerate(poles)]]
        cases.append({"id": "multiscale_" + str(index), "family": "separated_clusters", "degree": degree,
                      "scenarios": scenarios(rate, sets, [1.0, 0.96, 1.05])})
    for index, (degree, rate) in enumerate(((19, 0.37), (27, 1.7), (33, 0.14))):
        common = [0.11, 0.4, 1.5, 3.1, 8.0]
        sets = [common, common + [14.0], common + [10.0, 21.0], [0.13, 0.36, 1.7, 3.0, 7.3, 27.0]]
        cases.append({"id": "model_" + str(index), "family": "pole_model_uncertainty", "degree": degree,
                      "scenarios": scenarios(rate, sets, [1.08, 1.0, 0.91, 0.96])})
    return cases


def public_input(case):
    return {"degree": case["degree"], "scenarios": case["scenarios"]}


def suite_digest(cases):
    return hashlib.sha256(json.dumps(cases, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
