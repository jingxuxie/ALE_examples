import numpy as np
from scipy.optimize import linprog


def solve(case):
    fits = {}
    for track in case["tracks"]:
        calibration = track["calibration"]
        time = np.asarray(track["time_ms"])
        signal = np.asarray(track["signal"])
        weights = 1 / np.asarray(track["sigma"]) ** 2
        basis = (1 - np.exp(-time / calibration["decay_ms"]) * np.cos(
            2 * np.pi * time / calibration["period_ms"] + calibration["phase_rad"]
        )) / 2
        basis_mean = np.average(basis, weights=weights)
        signal_mean = np.average(signal, weights=weights)
        information = np.sum(weights * (basis - basis_mean) ** 2)
        amplitude = np.sum(weights * (basis - basis_mean) * (signal - signal_mean)) / information
        offset = signal_mean - amplitude * basis_mean
        query = np.asarray(track["query_time_ms"])
        query_basis = (1 - np.exp(-query / calibration["decay_ms"]) * np.cos(
            2 * np.pi * query / calibration["period_ms"] + calibration["phase_rad"]
        )) / 2
        fits[track["id"]] = {
            "offset": float(offset), "amplitude": float(amplitude),
            "amplitude_se": float(information ** -0.5),
            "prediction": (offset + amplitude * query_basis).tolist(),
        }
    occupation = case["occupation"]
    matrix, centers, radii = [], [], []
    for observation in occupation["observations"]:
        matrix.append(observation["response"])
        if "amplitude_weights" in observation:
            weights = observation["amplitude_weights"]
            centers.append(sum(weight * fits[name]["amplitude"] for name, weight in weights.items()))
            error = sum((weight * fits[name]["amplitude_se"]) ** 2 for name, weight in weights.items())
            radii.append(observation["sigma_multiplier"] * error ** 0.5 + observation["systematic_radius"])
        else:
            centers.append(observation["center"])
            radii.append(observation["radius"])
    matrix, centers, radii = map(np.asarray, (matrix, centers, radii))
    size = len(occupation["states"])
    relaxation = linprog(
        np.r_[np.zeros(size), 1.0],
        A_ub=np.vstack([np.column_stack([matrix, -radii]), np.column_stack([-matrix, -radii])]),
        b_ub=np.r_[centers + radii, radii - centers],
        A_eq=np.array([np.r_[np.ones(size), 0.0]]), b_eq=[1.0],
        bounds=(0, None), method="highs-ipm",
    )
    if not relaxation.success:
        raise RuntimeError(relaxation.message)
    inflation = max(0.0, float(relaxation.x[-1]))
    enlarged = radii * (1 + inflation + occupation["feasibility_pad"])
    inequalities = np.vstack([matrix, -matrix])
    limits = np.r_[centers + enlarged, enlarged - centers]
    bounds, witnesses = {}, {}
    for target in occupation["targets"]:
        coefficients = np.asarray(target["coefficients"])
        endpoints, distributions = [], {}
        for name, direction in [("lower", 1), ("upper", -1)]:
            result = linprog(
                direction * coefficients, A_ub=inequalities, b_ub=limits,
                A_eq=np.ones((1, size)), b_eq=[1.0], bounds=(0, None), method="highs-ipm",
            )
            if not result.success:
                raise RuntimeError(result.message)
            endpoints.append(float(coefficients @ result.x))
            distributions[name] = result.x.tolist()
        bounds[target["id"]] = endpoints
        witnesses[target["id"]] = distributions
    return {"fits": fits, "inflation": inflation, "bounds": bounds, "witnesses": witnesses}
