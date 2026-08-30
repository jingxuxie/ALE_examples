import math
import numpy as np


def validate(instance, answer):
    if not isinstance(answer, dict):
        raise ValueError("answer must be an object")
    selected = answer.get("selected")
    if not isinstance(selected, list) or any(type(index) is not int for index in selected):
        raise ValueError("tap indices must be integers")
    if len(selected) > instance["budget"] or selected != sorted(set(selected)):
        raise ValueError("invalid tap budget or ordering")
    if any(index < 0 or index >= len(instance["taps"]) for index in selected):
        raise ValueError("tap index out of range")
    table = answer.get("correction")
    if not isinstance(table, list) or len(table) != 1 << len(selected):
        raise ValueError("incorrect correction table length")
    if any(type(bit) is not int or bit not in (0, 1) for bit in table):
        raise ValueError("corrections must be binary integers")


def characteristic_distribution(instance, selected):
    width = len(selected)
    masks = [instance["taps"][index] for index in selected] + [1 << instance["detectors"]]
    parities = [0] * (1 << len(masks))
    for mask in range(1, len(parities)):
        lowest = mask & -mask
        parities[mask] = parities[mask ^ lowest] ^ masks[lowest.bit_length() - 1]
    characteristic = np.ones((len(instance["regimes"]), len(parities)), dtype=np.float64)
    for channel in instance["channels"]:
        factors = np.ones_like(characteristic)
        for branch, signature in enumerate(channel["signatures"]):
            odd = np.asarray([(mask & signature).bit_count() & 1 for mask in parities])
            probabilities = np.asarray([regime[branch] for regime in channel["probabilities"]])
            factors -= 2 * probabilities[:, None] * odd[None, :]
        characteristic *= factors
    for stage in range(len(masks)):
        step = 1 << stage
        shaped = characteristic.reshape(len(instance["regimes"]), -1, step * 2)
        left = shaped[:, :, :step].copy()
        right = shaped[:, :, step:].copy()
        shaped[:, :, :step] = left + right
        shaped[:, :, step:] = left - right
    distribution = characteristic / len(parities)
    if distribution.min() < -1e-12 or not np.allclose(distribution.sum(axis=1), 1, atol=1e-12):
        raise RuntimeError("invalid probability distribution")
    return np.maximum(distribution, 0).reshape(len(instance["regimes"]), 2, 1 << width).transpose(0, 2, 1)


def score_answer(instance, answer):
    validate(instance, answer)
    distribution = characteristic_distribution(instance, answer["selected"])
    table = np.asarray(answer["correction"], dtype=int)
    risks = distribution[:, np.arange(len(table)), 1 - table].sum(axis=1)
    if any(not math.isfinite(float(value)) for value in risks):
        raise ValueError("nonfinite risk")
    return {"regime_risks": risks.tolist(), "worst_risk": float(risks.max())}
