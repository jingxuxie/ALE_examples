from pathlib import Path
import os
import stat
import zipfile

import numpy as np

from physical import spectrum


def load_output(path, qubits, limit):
    path = Path(path)
    try:
        descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    except OSError as error:
        raise ValueError("output must be a readable nonsymlink file") from error
    with os.fdopen(descriptor, "rb") as stream:
        information = os.fstat(stream.fileno())
        if not stat.S_ISREG(information.st_mode) or information.st_size > 16 * 1024**2:
            raise ValueError("nonregular or oversized output")
        with zipfile.ZipFile(stream) as archive:
            if sum(entry.file_size for entry in archive.infolist()) > 32 * 1024**2:
                raise ValueError("oversized decompressed output")
        stream.seek(0)
        with np.load(stream, allow_pickle=False) as archive:
            if set(archive.files) != {"paulis", "probabilities", "p_identity"}:
                raise ValueError("output keys do not match schema")
            result = {key: archive[key] for key in archive.files}
    labels = result["paulis"]
    weights = result["probabilities"]
    identity = result["p_identity"]
    if labels.dtype != np.uint8 or labels.ndim != 2 or labels.shape[1] != qubits or len(labels) > limit:
        raise ValueError("invalid Pauli array")
    if np.any(labels > 3) or np.any(np.all(labels == 0, axis=1)) or len(np.unique(labels, axis=0)) != len(labels):
        raise ValueError("invalid, identity, or duplicate Pauli row")
    if weights.dtype != np.float64 or weights.shape != (len(labels),):
        raise ValueError("invalid probability array")
    if identity.dtype != np.float64 or identity.shape != ():
        raise ValueError("invalid identity scalar")
    if not np.all(np.isfinite(weights)) or np.any(weights < 0) or not np.isfinite(identity) or identity < 0:
        raise ValueError("probabilities must be finite and nonnegative")
    if float(identity) + float(weights.sum()) > 1 + 1e-8:
        raise ValueError("probability mass exceeds one")
    return result


def measure(prediction, truth, floor):
    expected = {row.tobytes(): float(weight) for row, weight in zip(truth["paulis"], truth["probabilities"])}
    predicted = {row.tobytes(): float(weight) for row, weight in zip(prediction["paulis"], prediction["probabilities"])}
    true_support = {key for key, value in expected.items() if value >= floor}
    predicted_support = {key for key, value in predicted.items() if value >= floor}
    intersection = len(true_support & predicted_support)
    precision = intersection / len(predicted_support) if predicted_support else 0.0
    recall = intersection / len(true_support) if true_support else 1.0
    f1 = 2 * intersection / (len(true_support) + len(predicted_support)) if true_support or predicted_support else 1.0
    remaining = max(0.0, 1.0 - float(prediction["p_identity"]) - sum(predicted.values()))
    union = set(expected) | set(predicted)
    ambient_inverse = 4.0 ** (-truth["paulis"].shape[1])
    uniform_atom = remaining * ambient_inverse
    l1 = sum(abs(expected.get(key, 0.0) - predicted.get(key, 0.0) - uniform_atom) for key in union)
    l1 += remaining * (1 - (len(union) + 1) * ambient_inverse)
    nonidentity_mass = float(np.sum(truth["probabilities"]))
    probability_error = l1 / nonidentity_mass
    predicted_spectrum = spectrum(prediction["paulis"], prediction["probabilities"], 0.0, truth["probe_paulis"])
    expected_spectrum = truth["probe_spectrum"] - float(truth["p_identity"])
    spectral_error = float(np.linalg.norm(predicted_spectrum - expected_spectrum) / np.linalg.norm(expected_spectrum))
    estimation_loss = (0.45 * probability_error + 0.20 * spectral_error) / 0.65
    loss = 0.65 * estimation_loss + 0.35 * (1 - f1)
    matched = true_support & set(predicted)
    matched_error = sum(abs(expected[key] - predicted[key]) for key in matched) / sum(expected[key] for key in matched) if matched else None
    return dict(loss=float(loss), estimation_loss=float(estimation_loss), recovery_score=float(f1), precision=float(precision), recall=float(recall), probability_relative_l1=float(probability_error), spectral_relative_l2=spectral_error, matched_probability_relative_l1=matched_error, significant_true=len(true_support), significant_predicted=len(predicted_support), significant_matched=intersection, unresolved_mass=remaining)


def rational(loss, strong, weak):
    scale = max(strong, 1e-4) * weak
    return float(scale / (scale + loss * loss))


def grade(metrics, calibration):
    reference = calibration["reference"]
    weak = calibration["weak"]
    return dict(**metrics, score=rational(metrics["loss"], reference["loss"], weak["loss"]), estimation_score=rational(metrics["estimation_loss"], reference["estimation_loss"], weak["estimation_loss"]))
