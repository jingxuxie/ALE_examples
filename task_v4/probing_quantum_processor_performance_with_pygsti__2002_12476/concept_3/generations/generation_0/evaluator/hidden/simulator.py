import math

import numpy as np


GATE_INPUT = np.array([[0., 0.], [1., 0.], [-1., 0.], [0., 1.], [0., -1.]])
PREPARATIONS = np.array([[1., 0., 0.], [-1., 0., 0.], [0., 1., 0.],
                         [0., -1., 0.], [0., 0., 1.], [0., 0., -1.]])
PARAMETER_SLICES = {
    "gate_bias": (0, 15, (5, 3)),
    "latent_vector": (15, 18, (3,)),
    "memory_matrix": (18, 24, (3, 2)),
    "retention": (24, 26, (2,)),
    "drift_sin": (26, 29, (3,)),
    "drift_cos": (29, 32, (3,)),
    "frequency": (32, 33, (1,)),
    "transition": (33, 41, (2, 4)),
    "reset": (41, 44, (3,)),
    "gamma": (44, 49, (5,)),
    "depolarization": (49, 54, (5,)),
}


def unpack(parameters):
    return {name: parameters[start:stop].reshape(shape)
            for name, (start, stop, shape) in PARAMETER_SLICES.items()}


def sample_parameters(generator):
    parameters = np.empty(54)
    fields = unpack(parameters)
    fields["gate_bias"][:] = generator.uniform(-0.018, 0.018, (5, 3))
    fields["latent_vector"][:2] = generator.uniform(-0.008, 0.008, 2)
    fields["latent_vector"][2] = generator.uniform(0.028, 0.062)
    fields["memory_matrix"][:2] = generator.uniform(-0.030, 0.030, (2, 2))
    fields["memory_matrix"][2] = generator.uniform(-0.070, 0.070, 2)
    fields["retention"][:] = generator.uniform(0.82, 0.97, 2)
    for name in ("drift_sin", "drift_cos"):
        fields[name][:2] = generator.uniform(-0.009, 0.009, 2)
        fields[name][2] = generator.uniform(-0.018, 0.018)
    fields["frequency"][:] = generator.uniform(0.8, 1.5)
    for column, interval in enumerate([(-5.8, -3.8), (-0.8, 0.8), (-1.1, 1.1), (-0.5, 0.5)]):
        fields["transition"][:, column] = generator.uniform(*interval, 2)
    fields["reset"][:] = [generator.uniform(-0.8, 0.8), generator.uniform(-1., 1.),
                           generator.uniform(-0.7, 0.7)]
    fields["gamma"][:] = generator.uniform(0.0001, 0.0012, 5)
    fields["depolarization"][:] = generator.uniform(0.0001, 0.0009, 5)
    return parameters


def _rotate(vector, rotation):
    angle = math.sqrt(np.dot(rotation, rotation))
    if angle < 1e-15:
        return vector.copy()
    axis = rotation / angle
    cosine = math.cos(angle)
    sine = math.sin(angle)
    cross = np.empty(3)
    cross[0] = axis[1] * vector[2] - axis[2] * vector[1]
    cross[1] = axis[2] * vector[0] - axis[0] * vector[2]
    cross[2] = axis[0] * vector[1] - axis[1] * vector[0]
    return cosine * vector + sine * cross + (1. - cosine) * np.dot(axis, vector) * axis


def _ideal(vector, gate):
    result = vector.copy()
    if gate == 1:
        result[1], result[2] = -vector[2], vector[1]
    elif gate == 2:
        result[1], result[2] = vector[2], -vector[1]
    elif gate == 3:
        result[0], result[2] = vector[2], -vector[0]
    elif gate == 4:
        result[0], result[2] = -vector[2], vector[0]
    return result


def _probabilities(parameters, gates, lengths, times, preparations, measurements):
    probabilities = np.empty(len(lengths))
    for row in range(len(lengths)):
        time = times[row]
        sine_time = math.sin(2. * math.pi * time)
        reset_logit = parameters[41] + parameters[42] * (2. * time - 1.) + parameters[43] * sine_time
        occupied = 1. / (1. + math.exp(-reset_logit))
        joint = np.zeros((2, 4))
        joint[0, 0], joint[1, 0] = 1. - occupied, occupied
        joint[0, 1:] = 0.985 * (1. - occupied) * PREPARATIONS[preparations[row]]
        joint[1, 1:] = 0.985 * occupied * PREPARATIONS[preparations[row]]
        memory = np.zeros(2)
        phase = 2. * math.pi * parameters[32] * time
        drift = parameters[26:29] * math.sin(phase) + parameters[29:32] * math.cos(phase)
        for position in range(lengths[row]):
            gate = gates[row, position]
            common_error = parameters[3 * gate:3 * gate + 3].copy() + drift
            for axis_index in range(3):
                common_error[axis_index] += parameters[18 + 2 * axis_index] * memory[0]
                common_error[axis_index] += parameters[19 + 2 * axis_index] * memory[1]
            gamma = parameters[44 + gate]
            attenuation = 1. - parameters[49 + gate]
            for state in range(2):
                error = common_error + (2 * state - 1) * parameters[15:18]
                vector = _rotate(_ideal(joint[state, 1:], gate), error)
                vector[0] *= math.sqrt(1. - gamma)
                vector[1] *= math.sqrt(1. - gamma)
                vector[2] = (1. - gamma) * vector[2] + gamma * joint[state, 0]
                joint[state, 1:] = attenuation * vector
            features = np.array([1., float(gate != 0), memory[0] - memory[1], sine_time])
            probability_01 = 1. / (1. + math.exp(-np.dot(parameters[33:37], features)))
            probability_10 = 1. / (1. + math.exp(-np.dot(parameters[37:41], features)))
            old_zero = joint[0].copy()
            old_one = joint[1].copy()
            joint[0] = (1. - probability_01) * old_zero + probability_10 * old_one
            joint[1] = probability_01 * old_zero + (1. - probability_10) * old_one
            for component in range(2):
                retention = parameters[24 + component]
                memory[component] = retention * memory[component] + (1. - retention) * GATE_INPUT[gate, component]
        expectation = joint[0, 1 + measurements[row]] + joint[1, 1 + measurements[row]]
        probabilities[row] = 0.008 + 0.979 * (1. - expectation) / 2.
    return probabilities


def predict(parameters, data):
    fields = unpack(np.asarray(parameters, dtype=np.float64))
    count = len(data["length"])
    sine_time = np.sin(2. * np.pi * data["time"])
    reset_logit = fields["reset"][0] + fields["reset"][1] * (2. * data["time"] - 1.) + fields["reset"][2] * sine_time
    occupied = 1. / (1. + np.exp(-reset_logit))
    joint = np.zeros((count, 2, 4))
    joint[:, 0, 0], joint[:, 1, 0] = 1. - occupied, occupied
    joint[:, :, 1:] = joint[:, :, :1] * (0.985 * PREPARATIONS[data["preparation"]])[:, None, :]
    memory = np.zeros((count, 2))
    phase = 2. * np.pi * fields["frequency"][0] * data["time"]
    drift = np.sin(phase)[:, None] * fields["drift_sin"] + np.cos(phase)[:, None] * fields["drift_cos"]
    ideal = np.array([np.column_stack([_ideal(np.eye(3)[axis], gate) for axis in range(3)]) for gate in range(5)])
    for position in range(int(np.max(data["length"]))):
        selected = data["length"] > position
        gates = data["gates"][selected, position]
        current = joint[selected].copy()
        common = fields["gate_bias"][gates] + drift[selected] + memory[selected] @ fields["memory_matrix"].T
        error = common[:, None, :] + np.array([-1., 1.])[None, :, None] * fields["latent_vector"]
        angle = np.linalg.norm(error, axis=2, keepdims=True)
        axis = error / np.where(angle > 0., angle, 1.)
        vector = np.einsum("nij,nsj->nsi", ideal[gates], current[:, :, 1:])
        vector = (np.cos(angle) * vector + np.sin(angle) * np.cross(axis, vector)
                  + (1. - np.cos(angle)) * np.sum(axis * vector, axis=2, keepdims=True) * axis)
        gamma = fields["gamma"][gates]
        vector[:, :, :2] *= np.sqrt(1. - gamma)[:, None, None]
        vector[:, :, 2] = (1. - gamma)[:, None] * vector[:, :, 2] + gamma[:, None] * current[:, :, 0]
        current[:, :, 1:] = (1. - fields["depolarization"][gates])[:, None, None] * vector
        features = np.column_stack([np.ones(len(gates)), gates != 0,
                                    memory[selected, 0] - memory[selected, 1], sine_time[selected]])
        transition = 1. / (1. + np.exp(-features @ fields["transition"].T))
        probability_01, probability_10 = transition[:, 0, None], transition[:, 1, None]
        joint[selected, 0] = (1. - probability_01) * current[:, 0] + probability_10 * current[:, 1]
        joint[selected, 1] = probability_01 * current[:, 0] + (1. - probability_10) * current[:, 1]
        memory[selected] = fields["retention"] * memory[selected] + (1. - fields["retention"]) * GATE_INPUT[gates]
    bloch = joint[:, :, 1:].sum(axis=1)
    expectation = bloch[np.arange(count), data["measurement"]]
    return 0.008 + 0.979 * (1. - expectation) / 2.


def predict_devices(parameters, data):
    predictions = np.empty(len(data["ids"]))
    for device in np.unique(data["device"]):
        selected = data["device"] == device
        subset = {key: value[selected] for key, value in data.items()}
        predictions[selected] = predict(parameters[int(device)], subset)
    if not np.all(np.isfinite(predictions)) or np.any(predictions < 0.) or np.any(predictions > 1.):
        raise ValueError("Physical simulator produced invalid probabilities")
    return predictions
