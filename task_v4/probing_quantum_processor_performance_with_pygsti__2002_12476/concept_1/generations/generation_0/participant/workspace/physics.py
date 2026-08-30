import json
from pathlib import Path

import numpy as np
from scipy.linalg import expm


FAMILIES = ("near_nominal", "long_coherence", "detuned", "anisotropic", "readout", "mixed")
PARAMETER_SCALES = np.array([0.01] * 9 + [0.001] * 3 + [0.02, 0.04])
AXES = np.array([[1., 0., 0.], [-1., 0., 0.], [0., 1., 0.],
                 [0., -1., 0.], [0., 0., 1.], [0., 0., -1.]])
MEASUREMENTS = np.eye(3)


def load_assets(root=None):
    root = Path(root) if root is not None else Path(__file__).resolve().parents[1]
    return (json.loads((root / "input/candidates.json").read_text()),
            json.loads((root / "input/contract.json").read_text()))


def nominal_parameters():
    return np.array([0.] * 9 + [0.002] * 3 + [0., 0.92])


def sample_parameters(rng, family):
    parameters = nominal_parameters()
    parameters[:9] = rng.uniform(-0.012, 0.012, 9)
    parameters[9:12] = rng.uniform(0.0008, 0.003, 3)
    parameters[12] = rng.uniform(-0.025, 0.025)
    parameters[13] = rng.uniform(0.90, 0.95)
    if family == "long_coherence":
        parameters[:9] = rng.uniform(-0.035, 0.035, 9)
        parameters[9:12] = rng.uniform(0.00004, 0.0003, 3)
    elif family == "detuned":
        parameters[[2, 5, 8]] = rng.uniform(-0.09, 0.09, 3)
    elif family == "anisotropic":
        parameters[9:12] = rng.uniform(0.0001, 0.001, 3)
        parameters[9 + int(rng.integers(3))] = rng.uniform(0.012, 0.030)
    elif family == "readout":
        parameters[12] = rng.uniform(-0.055, 0.055)
        parameters[13] = rng.uniform(0.76, 0.86)
    elif family == "mixed":
        parameters[:9] = rng.uniform(-0.06, 0.06, 9)
        parameters[9:12] = np.exp(rng.uniform(np.log(0.00006), np.log(0.025), 3))
        parameters[12] = rng.uniform(-0.05, 0.05)
        parameters[13] = rng.uniform(0.80, 0.94)
    elif family != "near_nominal":
        raise ValueError("unknown family")
    return parameters


def cross_matrix(vector):
    first, second, third = vector
    return np.array([[0., -third, second], [third, 0., -first], [-second, first, 0.]])


def gate_matrices(parameters):
    rotations = parameters[:9].reshape(3, 3).copy()
    rotations[0, 0] += np.pi / 2
    rotations[1, 1] += np.pi / 2
    return np.stack([np.exp(-parameters[9 + index]) * expm(cross_matrix(vector))
                     for index, vector in enumerate(rotations)])


def probabilities(parameters, candidates):
    gates = dict(zip("XYI", gate_matrices(parameters)))
    products = {}
    powers = {}
    result = np.empty(len(candidates))
    for index, circuit in enumerate(candidates):
        germ = circuit["germ"]
        repetitions = circuit["repetitions"]
        if germ not in products:
            product = np.eye(3)
            for label in germ:
                product = gates[label] @ product
            products[germ] = product
        key = (germ, repetitions)
        if key not in powers:
            powers[key] = np.linalg.matrix_power(products[germ], repetitions)
        expectation = MEASUREMENTS[circuit["measurement"]] @ powers[key] @ AXES[circuit["preparation"]]
        result[index] = (1 + parameters[12] + parameters[13] * expectation) / 2
    return result


def fisher_features(parameters, candidates, step=1e-6):
    base = probabilities(parameters, candidates)
    derivatives = np.empty((len(candidates), 14))
    for parameter in range(14):
        shifted_up = parameters.copy()
        shifted_down = parameters.copy()
        shifted_up[parameter] += step
        shifted_down[parameter] -= step
        derivatives[:, parameter] = (probabilities(shifted_up, candidates) -
                                      probabilities(shifted_down, candidates)) / (2 * step)
    return derivatives * PARAMETER_SCALES / np.sqrt(base * (1 - base))[:, None]


def design_cost(batches, candidates, contract):
    lengths = np.array([len(circuit["germ"]) * circuit["repetitions"] for circuit in candidates])
    return int(np.dot(batches, contract["shots_per_batch"] * (lengths + contract["reset_ticks"])) +
               np.count_nonzero(batches) * contract["setup_ticks"])


def validate_batches(value, candidates, contract):
    if not isinstance(value, list) or len(value) != len(candidates):
        raise ValueError("batches must be a list with one entry per candidate")
    if any(type(entry) is not int for entry in value):
        raise ValueError("batches must contain integers, not floats or booleans")
    batches = np.array(value, dtype=np.int64)
    if np.any(batches < 0) or np.any(batches > contract["max_batches_per_circuit"]):
        raise ValueError("per-circuit batch limit violated")
    if not 1 <= np.count_nonzero(batches) <= contract["max_distinct_circuits"]:
        raise ValueError("distinct circuit limit violated")
    cost = design_cost(batches, candidates, contract)
    if cost > contract["execution_budget_ticks"]:
        raise ValueError("execution budget exceeded")
    return batches, cost


def risks(features, batches, shots=64):
    information = shots * np.einsum("sci,c,scj->sij", features, batches, features, optimize=True)
    information += np.eye(14)[None] * 1e-10
    covariance = np.linalg.inv(information)
    return np.maximum(np.trace(covariance[:, :12, :12], axis1=1, axis2=2), 0.)


def score_risks(candidate_risks, baseline_risks, families):
    family_scores = {}
    for family in FAMILIES:
        mask = families == family
        family_scores[family] = float(1 - candidate_risks[mask].mean() / baseline_risks[mask].mean())
    return float(1 - candidate_risks.mean() / baseline_risks.mean()), family_scores
