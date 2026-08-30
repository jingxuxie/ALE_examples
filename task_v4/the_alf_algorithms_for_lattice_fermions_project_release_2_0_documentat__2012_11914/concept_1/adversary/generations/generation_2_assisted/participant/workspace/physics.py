import argparse
import json
from pathlib import Path

import numpy as np
from scipy.linalg import expm


MODEL_PATH = Path(__file__).resolve().parents[1] / "input" / "model.json"


def load_model():
    return json.loads(MODEL_PATH.read_text())


def kinetic_matrix(size=4, hopping=1.0):
    matrix = np.zeros((size * size, size * size))
    for horizontal in range(size):
        for vertical in range(size):
            source = horizontal * size + vertical
            for delta_horizontal, delta_vertical in [(1, 0), (0, 1)]:
                target = ((horizontal + delta_horizontal) % size) * size + (vertical + delta_vertical) % size
                matrix[source, target] = matrix[target, source] = -hopping
    return matrix


def weight_batch(fields, model=None, point=None):
    model = load_model() if model is None else model
    point = model["certification_points"][0] if point is None else point
    fields = np.asarray(fields)
    if fields.ndim == 2:
        fields = fields[None]
    beta = model["beta"] * point["beta_multiplier"]
    chemical = model["chemical_potential"] + point["chemical_shift"]
    delta = beta / model["time_slices"]
    coupling = np.arccosh(np.exp(delta * model["interaction"] / 2))
    kinetic = expm(-delta * kinetic_matrix(model["linear_size"], model["hopping"]))
    sites = model["linear_size"] ** 2
    products = np.broadcast_to(np.eye(sites), (len(fields), 2, sites, sites)).copy()
    for time_index in range(model["time_slices"]):
        diagonal = np.exp(coupling * fields[:, time_index, None, :] * np.array([1, -1])[None, :, None])
        products = kinetic @ (diagonal[..., :, None] * products)
    signs, logabs = np.linalg.slogdet(np.eye(sites) + np.exp(beta * chemical) * products)
    return np.prod(signs, axis=1), np.sum(logabs, axis=1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("witness")
    arguments = parser.parse_args()
    payload = json.loads(Path(arguments.witness).read_text())
    model = load_model()
    for point in model["certification_points"]:
        signs, logabs = weight_batch(payload["fields"], model, point)
        print(json.dumps({"point": point, "sign": float(signs[0]), "logabs_weight": float(logabs[0])}))
