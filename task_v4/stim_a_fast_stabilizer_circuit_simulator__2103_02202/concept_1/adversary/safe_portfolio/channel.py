import numpy as np


def marginals(instance, selected):
    width = len(selected)
    size = 1 << (width + 1)
    regimes = len(instance["regimes"])
    distribution = np.zeros((regimes, size), dtype=np.float64)
    distribution[:, 0] = 1
    indices = np.arange(size)
    taps = [instance["taps"][index] for index in selected]
    for channel in instance["channels"]:
        probabilities = np.asarray(channel["probabilities"], dtype=np.float64)
        updated = distribution * (1 - probabilities.sum(axis=1))[:, None]
        for branch, signature in enumerate(channel["signatures"]):
            projected = (signature >> instance["detectors"]) << width
            for position, tap in enumerate(taps):
                projected |= ((signature & tap).bit_count() & 1) << position
            updated += distribution[:, indices ^ projected] * probabilities[:, branch, None]
        distribution = updated
    return distribution.reshape(regimes, 2, 1 << width).transpose(0, 2, 1)


def fit_table(distribution):
    average = distribution.mean(axis=0)
    table = (average[:, 1] > average[:, 0]).astype(np.int8)
    risks = distribution[:, np.arange(len(table)), 1 - table].sum(axis=1)
    for iteration in range(3):
        changed = False
        for syndrome in range(len(table)):
            delta = distribution[:, syndrome, table[syndrome]] - distribution[:, syndrome, 1 - table[syndrome]]
            candidate = risks + delta
            if (float(candidate.max()), float(candidate.mean())) < (float(risks.max()), float(risks.mean())):
                table[syndrome] ^= 1
                risks = candidate
                changed = True
        if not changed:
            break
    return table.tolist(), risks.tolist()


def risk(instance, answer):
    distribution = marginals(instance, answer["selected"])
    table = np.asarray(answer["correction"], dtype=np.int8)
    return distribution[:, np.arange(len(table)), 1 - table].sum(axis=1).tolist()
