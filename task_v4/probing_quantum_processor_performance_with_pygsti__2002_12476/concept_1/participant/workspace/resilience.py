import itertools

import numpy as np


def risk_profile(features, batches, removed, shots):
    support = np.flatnonzero(batches)
    counts = batches[support] * shots
    cases = list(itertools.combinations(range(len(support)), min(removed, len(support))))
    loss_counts = np.tile(counts, (len(cases), 1))
    for index, case in enumerate(cases):
        loss_counts[index, list(case)] = 0
    intact_risks = []
    loss_risks = []
    worst_pairs = []
    for model_features in features:
        rows = model_features[support]
        all_counts = np.concatenate([counts[None], loss_counts], axis=0)
        information = np.einsum("ci,kc,cj->kij", rows, all_counts, rows, optimize=True)
        information += np.eye(14)[None] * 1e-10
        if np.any(np.linalg.eigvalsh(information)[:, 0] <= 0):
            raise ValueError("numerically nonpositive information")
        covariance = np.linalg.inv(information)
        risks = np.trace(covariance[:, :12, :12], axis1=1, axis2=2)
        if not np.all(np.isfinite(risks)) or np.any(risks <= 0):
            raise ValueError("nonpositive or nonfinite information risk")
        worst = int(np.argmax(risks[1:]))
        intact_risks.append(float(risks[0]))
        loss_risks.append(float(risks[1 + worst]))
        worst_pairs.append(support[list(cases[worst])].tolist())
    return np.array(intact_risks), np.array(loss_risks), worst_pairs
