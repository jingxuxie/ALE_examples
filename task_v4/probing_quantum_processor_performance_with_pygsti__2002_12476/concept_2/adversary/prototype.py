import argparse
import itertools
import json
import time
from pathlib import Path

import numpy as np
from scipy.optimize import minimize


FIDUCIALS = ["", "X", "Y", "XX", "XXX", "YY"]
PAIRS = {
    "I": [(0, 3), (1, 1), (5, 5)],
    "X": [(1, 1), (3, 4), (4, 2), (5, 5)],
    "Y": [(0, 2), (2, 2), (2, 4), (4, 4)],
    "XY": [(0, 0), (0, 4), (2, 5), (5, 4)],
    "XXY": [(1, 3), (1, 4), (3, 5), (5, 0), (5, 4), (5, 5)],
}
PAULIS = np.array([
    [[1, 0], [0, 1]], [[0, 1], [1, 0]],
    [[0, -1j], [1j, 0]], [[1, 0], [0, -1]],
], dtype=complex)
IDEALS = np.array([PAULIS[0], (PAULIS[0] - 1j * PAULIS[1]) / np.sqrt(2),
                   (PAULIS[0] - 1j * PAULIS[2]) / np.sqrt(2)])


def circuits():
    families = {}
    families["short"] = ["".join(word) for length in range(5)
                          for word in itertools.product("IXY", repeat=length)]
    for germ, pairs in PAIRS.items():
        families[germ] = sorted(set(
            FIDUCIALS[prep] + germ * max(1, depth // len(germ)) + FIDUCIALS[meas]
            for depth in [1, 2, 4, 8, 16, 32, 64] for prep, meas in pairs))
    generator = np.random.default_rng(200212476)
    families["guards"] = ["".join(generator.choice(list("IXY"), 64)) for index in range(32)]
    return families


def encode(words):
    encoded = np.full((len(words), max(map(len, words), default=0)), 3, dtype=int)
    for index, word in enumerate(words):
        encoded[index, :len(word)] = ["IXY".index(symbol) for symbol in word]
    return encoded


def operators(parameters):
    rows = np.asarray(parameters).reshape(3, 5)
    unitaries = [np.eye(3, dtype=complex) for index in range(4)]
    for index, row in enumerate(rows):
        couplings = np.array([row[1] + 1j * row[2], row[3] + 1j * row[4]])
        hamiltonian = np.zeros((3, 3), dtype=complex)
        hamiltonian[:2, 2] = couplings
        hamiltonian[2, :2] = couplings.conj()
        radius = np.linalg.norm(couplings)
        mixing = np.eye(3) - 1j * np.sinc(radius / np.pi) * hamiltonian
        mixing -= 0.5 * np.sinc(radius / (2 * np.pi)) ** 2 * (hamiltonian @ hamiltonian)
        nominal = np.zeros((3, 3), dtype=complex)
        nominal[:2, :2] = IDEALS[index]
        nominal[2, 2] = np.exp(-1j * row[0])
        unitaries[index] = mixing @ nominal
    transfers = []
    for unitary in unitaries:
        first = unitary[:2, :2]
        second = np.zeros((2, 2), dtype=complex)
        second[1] = unitary[2, :2]
        images = first @ PAULIS @ first.conj().T + second @ PAULIS @ second.conj().T
        transfers.append((np.einsum("aij,bji->ab", PAULIS, images) / 2).real)
    return np.asarray(unitaries), np.asarray(transfers)


def simulate(parameters, encoded):
    unitaries, transfers = operators(parameters)
    states = np.zeros((len(encoded), 3), dtype=complex)
    states[:, 0] = 1
    bloch = np.tile([1., 0., 0., 1.], (len(encoded), 1))
    for column in encoded.T:
        states = (unitaries[column] @ states[..., None])[..., 0]
        bloch = (transfers[column] @ bloch[..., None])[..., 0]
    truth = .005 + .99 * np.abs(states[:, 0]) ** 2
    prediction = .005 + .99 * (bloch[:, 0] + bloch[:, 3]) / 2
    leakage = np.abs(states[:, 2]) ** 2
    return truth - prediction, leakage


def optimize_circuit(parameters, generator, population=2048, rounds=40):
    encoded = generator.integers(0, 3, size=(population, 64))
    best_score = -np.inf
    best_word = None
    for generation in range(rounds):
        residual, leakage = simulate(parameters, encoded)
        scores = np.abs(residual)
        order = np.argsort(scores)
        if scores[order[-1]] > best_score:
            best_score = float(scores[order[-1]])
            best_word = encoded[order[-1]].copy()
            best_leakage = float(leakage[order[-1]])
        elite = encoded[order[-128:]]
        encoded = elite[generator.integers(0, len(elite), population)].copy()
        mutation_count = 1 if generation > rounds // 2 else 3
        for mutation in range(mutation_count):
            locations = generator.integers(0, 64, population)
            encoded[np.arange(population), locations] = generator.integers(0, 3, population)
        encoded[:len(elite)] = elite
    return "".join("IXY"[index] for index in best_word), best_score, best_leakage


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--trials", type=int, default=24)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    start = time.monotonic()
    generator = np.random.default_rng(830121)
    calibration = encode(sum(circuits().values(), []))
    results = []
    for trial in range(args.trials):
        parameters = generator.normal(0, .007, (3, 5))
        parameters[:, 0] = generator.uniform(-np.pi, np.pi, 3)
        parameters = parameters.ravel()
        residual, leakage = simulate(parameters, calibration)
        parameters.reshape(3, 5)[:, 1:] *= min(1, np.sqrt(.005 / max(abs(residual))))
        residual, leakage = simulate(parameters, calibration)
        word, score, final_leakage = optimize_circuit(parameters, generator, 1024, 30)
        record = {"parameters": parameters.tolist(), "circuit": word,
                  "calibration_max": float(max(abs(residual))),
                  "calibration_rms": float(np.sqrt(np.mean(residual ** 2))),
                  "heldout": score, "final_leakage": final_leakage}
        results.append(record)
        print(trial, json.dumps(record), "seconds", time.monotonic() - start, flush=True)
    if args.output:
        args.output.write_text(json.dumps(results, indent=2) + "\n")


if __name__ == "__main__":
    main()
