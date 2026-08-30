import itertools
import numpy as np

NSITES = 6
STATES = np.array([value for value in range(64) if value.bit_count() == 3], dtype=int)
OCCUPATIONS = ((STATES[:, None] >> np.arange(NSITES)) & 1).astype(float)
SPINS = OCCUPATIONS - 0.5
STATE_INDEX = {int(state): index for index, state in enumerate(STATES)}
LOWER = np.array([0.55] * 6 + [-0.5] * 5 + [0.3, 0.05, 0.05] + [0.002] * 6)
UPPER = np.array([1.45] * 6 + [0.5] * 5 + [1.7, 0.5, 0.5] + [0.05] * 6)
PARAMETER_NAMES = [f"J{site}" for site in range(6)] + [f"h{site}" for site in range(5)] + ["Delta", "K0", "K1"] + [f"e{site}" for site in range(6)]
BONDS = [(site, (site + offset) % NSITES) for offset in (1, 2) for site in range(NSITES)]
EXCHANGE = np.zeros((12, len(STATES), len(STATES)))
ISING = np.zeros((12, len(STATES)))
for bond_index, (left, right) in enumerate(BONDS):
    ISING[bond_index] = SPINS[:, left] * SPINS[:, right]
    for state_index, state in enumerate(STATES):
        if ((state >> left) & 1) != ((state >> right) & 1):
            EXCHANGE[bond_index, STATE_INDEX[int(state) ^ (1 << left) ^ (1 << right)], state_index] = 0.5
OUTCOME_BITS = ((np.arange(64)[:, None] >> np.arange(NSITES)) & 1)
READOUT_DIFFERENCES = OUTCOME_BITS[:, None, :] != OCCUPATIONS[None, :, :]


def hamiltonian(parameters):
    parameters = np.asarray(parameters, dtype=float)
    couplings = np.concatenate((parameters[:6], parameters[12 + np.arange(6) % 2]))
    fields = np.append(parameters[6:11], -np.sum(parameters[6:11]))
    matrix = np.einsum("b,bij->ij", couplings, EXCHANGE)
    matrix[np.diag_indices(len(STATES))] += parameters[11] * (couplings @ ISING) + SPINS @ fields
    return matrix


def predict_many(parameters, experiments):
    parameters = np.asarray(parameters, dtype=float)
    energies, vectors = np.linalg.eigh(hamiltonian(parameters))
    detector = np.prod(np.where(READOUT_DIFFERENCES, parameters[14:20], 1.0 - parameters[14:20]), axis=2)
    predictions = []
    for experiment in experiments:
        half_phase = np.exp(-0.5j * float(experiment["time"]) * energies)
        state = vectors @ (half_phase * vectors[STATE_INDEX[int(experiment["preparation"])], :])
        state *= np.exp(-1j * (OCCUPATIONS @ np.asarray(experiment["phases"])))
        state = vectors @ (half_phase * (vectors.T @ state))
        probability = np.maximum(detector @ np.abs(state) ** 2, 0.0)
        predictions.append(probability / probability.sum())
    return np.asarray(predictions)


def probabilities(parameters, experiment):
    return predict_many(parameters, [experiment])[0]


def validate_experiment(experiment):
    if set(experiment) != {"type", "preparation", "time", "phases"} or experiment["type"] != "query":
        raise ValueError("query requires exactly type, preparation, time, and phases")
    preparation = experiment["preparation"]
    if isinstance(preparation, bool) or not isinstance(preparation, int) or preparation not in STATE_INDEX:
        raise ValueError("preparation must be a six-bit three-up-spin mask")
    duration = experiment["time"]
    if isinstance(duration, bool) or not isinstance(duration, (int, float)) or not np.isfinite(duration) or not 0 <= duration <= 6:
        raise ValueError("time must be finite and between zero and six")
    if not isinstance(experiment["phases"], list) or len(experiment["phases"]) != NSITES:
        raise ValueError("six midpoint phases required")
    for phase in experiment["phases"]:
        if isinstance(phase, bool) or not isinstance(phase, (int, float)) or not np.isfinite(phase) or abs(phase) > np.pi:
            raise ValueError("phase outside [-pi,pi]")
    return experiment
