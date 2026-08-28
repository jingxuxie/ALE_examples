import numpy as np

from reference.engine import feasible_actions, risk, spectrum


WEIGHTS = dict(calibration=0.25, audit=0.30, dynamics=0.30, decision=0.15)
FLOORS = dict(calibration=0.01, audit=0.01, dynamics=0.0001, decision=0.002)


def finite_array(value, shape):
    array = np.asarray(value, dtype=float)
    if array.shape != shape or not np.isfinite(array).all():
        raise ValueError(f"expected finite array of shape {shape}")
    return array


def bath_error(result, reference):
    bath = result["bath"]
    if bath["beta"] not in (0, 1, 2):
        raise ValueError("beta must be 0, 1, or 2")
    for key, lower, upper in (("amplitude", 1e-5, 0.12), ("eta", 0, 1)):
        if not lower <= bath[key] <= upper:
            raise ValueError(f"out-of-bounds {key}")
    if bath["beta"]:
        for key, lower, upper in (("cutoff", 0.12, 1.2), ("floor", 0, 0.02)):
            if not lower <= bath[key] <= upper:
                raise ValueError(f"out-of-bounds {key}")
    frequencies = np.r_[0.0, np.geomspace(0.02, 30, 33)]
    ratios = spectrum(bath, frequencies) / spectrum(reference["bath"], frequencies)
    return float(np.mean(np.log(ratios)**2) + 4 * (bath["eta"] - reference["bath"]["eta"])**2)


def audit_error(result, reference):
    if len(result["audit"]) != len(reference["audit"]):
        raise ValueError("wrong audit length")
    errors = []
    for actual, expected in zip(result["audit"], reference["audit"]):
        derivative = finite_array(actual["real"], (64, 64)) + 1j * finite_array(actual["imag"], (64, 64))
        target = np.asarray(expected["real"]) + 1j * np.asarray(expected["imag"])
        activity = finite_array(actual["activity"], (3,))
        target_activity = np.asarray(expected["activity"])
        errors.append(0.5 * np.linalg.norm(derivative - target)**2 / (np.linalg.norm(target)**2 + 1e-16)
                      + 0.5 * np.linalg.norm(activity - target_activity)**2
                      / (np.linalg.norm(target_activity)**2 + 1e-16))
    return float(np.mean(errors))


def prediction_array(prediction, count):
    return np.column_stack([finite_array(prediction["gauge"], (count,)),
                            finite_array(prediction["fidelity"], (count,)),
                            0.5 * finite_array(prediction["electric"], (count,)),
                            finite_array(prediction["density"], (count, 3))])


def raw_errors(case, result, reference):
    errors, messages = {}, {}
    for component in WEIGHTS:
        try:
            if component == "calibration":
                error = bath_error(result, reference)
            elif component == "audit":
                error = audit_error(result, reference)
            elif component == "dynamics":
                error = np.mean([np.mean((prediction_array(result["predictions"][action["id"]], len(case["times"]))
                                         - prediction_array(reference["predictions"][action["id"]], len(case["times"])))**2)
                                 for action in feasible_actions(case)])
            else:
                selected = result["selected_action"]
                identifiers = [action["id"] for action in feasible_actions(case)]
                if selected not in identifiers:
                    raise ValueError("selected action is not feasible")
                risks = {identifier: risk(case, reference["predictions"][identifier]) for identifier in identifiers}
                error = max(0, risks[selected] - min(risks.values()))
            if not np.isfinite(error):
                raise ValueError("nonfinite error")
            errors[component] = float(error)
        except (KeyError, TypeError, ValueError, OverflowError, IndexError) as exception:
            errors[component] = None
            messages[component] = str(exception)
    return errors, messages


def score_result(case, result, label):
    errors, messages = raw_errors(case, result, label["reference"])
    components = {name: (0.0 if error is None else 1 / (1 + error / label["anchors"][name]))
                  for name, error in errors.items()}
    core = sum(WEIGHTS[name] * components[name] for name in WEIGHTS)
    return dict(core=float(core), components=components, raw_errors=errors, validation_errors=messages)


def summarize(cases):
    families = sorted(set(record["family"] for record in cases))
    family_scores = {family: float(np.mean([record["core"] for record in cases if record["family"] == family]))
                     for family in families}
    mean_core = float(np.mean([record["core"] for record in cases]))
    worst_family = min(family_scores.values())
    components = {name: float(np.mean([record["components"][name] for record in cases])) for name in WEIGHTS}
    return dict(mean_core=mean_core, worst_family=worst_family, family_scores=family_scores,
                component_scores=components, score=0.7 * mean_core + 0.3 * worst_family, cases=cases)
