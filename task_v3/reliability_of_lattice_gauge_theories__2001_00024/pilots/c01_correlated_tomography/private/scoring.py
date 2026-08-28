import numpy as np


def finite_array(value, shape):
    result = np.asarray(value, dtype=float)
    if result.shape != shape or not np.all(np.isfinite(result)):
        raise ValueError(f"Expected finite array with shape {shape}")
    return result


def losses(case, truth, answer):
    fit_terms = []
    for track in case["tracks"]:
        expected = truth["fits"][track["id"]]
        submitted = answer["fits"][track["id"]]
        for key, scale in [("amplitude", 0.025), ("offset", 0.015), ("amplitude_se", 0.005)]:
            value = finite_array(submitted[key], ())
            fit_terms.append(float(((value - expected[key]) / scale) ** 2))
        prediction = finite_array(submitted["prediction"], (len(track["query_time_ms"]),))
        fit_terms.append(float(np.mean(((prediction - expected["prediction"]) / 0.03) ** 2)))
    inflation = float(finite_array(answer["inflation"], ()))
    inference_terms = [((inflation - truth["inflation"]) / 0.1) ** 2]
    matrix = np.asarray(truth["matrix"])
    centers = np.asarray(truth["centers"])
    radii = np.asarray(truth["radii"]) * (
        1 + truth["inflation"] + case["occupation"]["feasibility_pad"]
    )
    size = len(case["occupation"]["states"])
    for target in case["occupation"]["targets"]:
        identifier = target["id"]
        endpoints = finite_array(answer["bounds"][identifier], (2,))
        expected = np.asarray(truth["bounds"][identifier])
        inference_terms.append(float(np.mean(((endpoints - expected) / 0.025) ** 2)))
        inference_terms.append(float((max(0, endpoints[0] - endpoints[1]) / 0.01) ** 2))
        for position, name in enumerate(["lower", "upper"]):
            distribution = finite_array(answer["witnesses"][identifier][name], (size,))
            violation = np.maximum(np.abs(matrix @ distribution - centers) - radii, 0)
            feasibility = max(
                abs(float(distribution.sum()) - 1), max(0, -float(distribution.min())),
                float(violation.max()),
            )
            attainment = abs(float(distribution @ target["coefficients"]) - endpoints[position])
            inference_terms.extend([(feasibility / 0.01) ** 2, (attainment / 0.01) ** 2])
    values = {"readout": float(np.mean(fit_terms)), "certificate": float(np.mean(inference_terms))}
    if not all(np.isfinite(value) for value in values.values()):
        raise ValueError("Non-finite numerical loss")
    return values


def score(case, truth, answer):
    error = losses(case, truth, answer)
    components = {
        name: 1 / (1 + value / max(truth["weak_losses"][name], 1e-4))
        for name, value in error.items()
    }
    return {
        "core": float(np.sqrt(components["readout"] * components["certificate"])),
        "components": components, "losses": error,
    }
