import json
from pathlib import Path

import numpy as np
import stim


SPECS = [{'case_id': 'r2_pairs_9', 'family': 'overlapping_spatial_pairs', 'distance': 9, 'rounds': 1, 'px': 0.004, 'pz': 0.01, 'py': 0.045, 'pair': 0.024, 'measurement': 0.0, 'burst': 0.0, 'profile': 'uniform'}, {'case_id': 'r2_pairs_11', 'family': 'overlapping_spatial_pairs', 'distance': 11, 'rounds': 1, 'px': 0.004, 'pz': 0.01, 'py': 0.045, 'pair': 0.032, 'measurement': 0.0, 'burst': 0.0, 'profile': 'uniform'}, {'case_id': 'r2_strip_9', 'family': 'known_nonuniform_crosstalk', 'distance': 9, 'rounds': 1, 'px': 0.005, 'pz': 0.006, 'py': 0.045, 'pair': 0.018, 'measurement': 0.0, 'burst': 0.0, 'profile': 'detector_support_strip'}, {'case_id': 'r2_strip_11', 'family': 'known_nonuniform_crosstalk', 'distance': 11, 'rounds': 1, 'px': 0.005, 'pz': 0.006, 'py': 0.045, 'pair': 0.02, 'measurement': 0.0, 'burst': 0.0, 'profile': 'detector_support_strip'}, {'case_id': 'r2_joint_7_r3', 'family': 'space_time_pair_memory', 'distance': 7, 'rounds': 3, 'px': 0.003, 'pz': 0.005, 'py': 0.025, 'pair': 0.014, 'measurement': 0.014, 'burst': 0.009, 'profile': 'uniform'}, {'case_id': 'r2_round_9_r3', 'family': 'space_time_pair_memory', 'distance': 9, 'rounds': 3, 'px': 0.003, 'pz': 0.005, 'py': 0.025, 'pair': 0.014, 'measurement': 0.008, 'burst': 0.008, 'profile': 'noisy_middle_round'}]


def make_uniform_model(spec):
    distance = spec["distance"]
    rounds = spec["rounds"]
    plane = distance * distance
    detector_count = 2 * plane * rounds
    mechanisms = []
    coordinates = []

    def vertex(column, row):
        return (row % distance) * distance + column % distance

    def component(axis, column, row, pauli, time):
        column %= distance
        row %= distance
        offset = 2 * plane * time
        if pauli == "Z":
            detectors = [offset + vertex(column, row), offset + vertex(column + (axis == 0), row + (axis == 1))]
            logicals = [axis] if (column if axis == 0 else row) == distance - 1 else []
        else:
            detectors = [offset + plane + vertex(column, row), offset + plane + vertex(column - (axis == 1), row - (axis == 0))]
            logicals = [2 + axis] if (row if axis == 0 else column) == 0 else []
        return detectors, logicals

    def add(probability, pieces, kind):
        if probability > 0:
            mechanisms.append((probability, pieces, kind))

    for time in range(rounds):
        for sector in range(2):
            for row in range(distance):
                for column in range(distance):
                    coordinates.append([column, row, time, sector])
        for axis in range(2):
            for row in range(distance):
                for column in range(distance):
                    part_x = component(axis, column, row, "X", time)
                    part_z = component(axis, column, row, "Z", time)
                    add(spec["px"], [part_x], "X")
                    add(spec["pz"], [part_z], "Z")
                    add(spec["py"], [part_x, part_z], "Y")
                    neighbor_column = column + (axis == 1)
                    neighbor_row = row + (axis == 0)
                    neighbor_x = component(axis, neighbor_column, neighbor_row, "X", time)
                    neighbor_z = component(axis, neighbor_column, neighbor_row, "Z", time)
                    add(spec["pair"], [part_x, neighbor_x], "XX")
                    add(spec["pair"] * 0.7, [part_z, neighbor_z], "ZZ")
                    if time + 1 < rounds:
                        later_x = component(axis, column, row, "X", time + 1)
                        later_z = component(axis, column, row, "Z", time + 1)
                        add(spec["burst"], [part_x, part_z, later_x, later_z], "YY_time")
        if time + 1 < rounds:
            for position in range(2 * plane):
                add(spec["measurement"], [([2 * plane * time + position, 2 * plane * (time + 1) + position], [])], "readout")
    detector_matrix = np.zeros((detector_count, len(mechanisms)), dtype=np.uint8)
    observable_matrix = np.zeros((4, len(mechanisms)), dtype=np.uint8)
    lines = []
    for index, (probability, pieces, kind) in enumerate(mechanisms):
        text_pieces = []
        for detectors, logicals in pieces:
            for detector in detectors:
                detector_matrix[detector, index] ^= 1
            for logical in logicals:
                observable_matrix[logical, index] ^= 1
            text_pieces.append(" ".join([f"D{detector}" for detector in detectors] + [f"L{logical}" for logical in logicals]))
        lines.append(f"error({probability:.17g}) " + " ^ ".join(text_pieces))
    for detector, coordinate in enumerate(coordinates):
        lines.append(f"detector({','.join(map(str, coordinate))}) D{detector}")
    lines.append("logical_observable L3")
    dem_text = "\n".join(lines) + "\n"
    dem = stim.DetectorErrorModel(dem_text)
    assert dem.num_detectors == detector_count
    assert dem.num_errors == len(mechanisms)
    return dict(spec, detector_matrix=detector_matrix, observable_matrix=observable_matrix,
                probabilities=np.asarray([entry[0] for entry in mechanisms]),
                detector_coordinates=np.asarray(coordinates, dtype=np.int64),
                mechanism_kind=np.asarray([entry[2] for entry in mechanisms]), dem_text=dem_text,
                num_detectors=detector_count, num_observables=4, num_mechanisms=len(mechanisms))


def sample_model(model, shots, seed):
    generator = np.random.Generator(np.random.PCG64DXSM(seed))
    faults = generator.random((shots, model["num_mechanisms"])) < model["probabilities"]
    syndromes = np.zeros((shots, model["num_detectors"]), dtype=np.uint8)
    observables = np.zeros((shots, 4), dtype=np.uint8)
    for mechanism in range(model["num_mechanisms"]):
        activated = faults[:, mechanism].astype(np.uint8)
        for detector in np.flatnonzero(model["detector_matrix"][:, mechanism]):
            syndromes[:, detector] ^= activated
        for logical in np.flatnonzero(model["observable_matrix"][:, mechanism]):
            observables[:, logical] ^= activated
    return syndromes, observables, faults.astype(np.uint8)


def save_model(model, directory):
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    arrays = {key: value for key, value in model.items() if isinstance(value, np.ndarray)}
    metadata = {key: value for key, value in model.items() if not isinstance(value, np.ndarray) and key != "dem_text"}
    (directory / "case.json").write_text(json.dumps(metadata, indent=2) + "\n")
    (directory / "model.dem").write_text(model["dem_text"])
    np.savez_compressed(directory / "model.npz", **arrays)


def load_model(directory):
    directory = Path(directory)
    model = json.loads((directory / "case.json").read_text())
    with np.load(directory / "model.npz", allow_pickle=False) as arrays:
        model.update({name: arrays[name] for name in arrays.files})
    model["dem_text"] = (directory / "model.dem").read_text()
    return model


def make_model(spec):
    model = make_uniform_model(spec)
    probabilities = model["probabilities"].copy()
    profile = spec["profile"]
    coordinates = model["detector_coordinates"]
    if profile == "detector_support_strip":
        selected = coordinates[:, 0] <= 1
        touched = np.any(model["detector_matrix"][selected] != 0, axis=0)
        probabilities[touched] *= 2.0
    elif profile == "noisy_middle_round":
        selected = coordinates[:, 2] == spec["rounds"] // 2
        touched = np.any(model["detector_matrix"][selected] != 0, axis=0)
        kinds = model["mechanism_kind"]
        probabilities[touched & (kinds == "readout")] *= 4.0
        probabilities[touched & (kinds == "YY_time")] *= 2.0
        probabilities[touched & np.isin(kinds, ["X", "Z", "Y"])] *= 1.5
    elif profile != "uniform":
        raise ValueError("Unknown profile")
    probabilities = np.clip(probabilities, 1e-8, 0.25)
    lines = model["dem_text"].splitlines()
    for mechanism, probability in enumerate(probabilities):
        suffix = lines[mechanism].split(")", 1)[1]
        lines[mechanism] = f"error({probability:.17g})" + suffix
    model["probabilities"] = probabilities
    model["dem_text"] = "\n".join(lines) + "\n"
    assert stim.DetectorErrorModel(model["dem_text"]).num_errors == len(probabilities)
    return model
