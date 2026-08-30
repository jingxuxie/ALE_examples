import numpy as np
from descriptors import describe_batch


def feature_matrix(cases):
    values = np.asarray([case['fields'] for case in cases], dtype=np.float64)
    values = values - values.mean(axis=1, keepdims=True)
    count, length = values.shape
    sites = np.arange(length)
    phase = np.exp(2j * np.pi * sites / length)
    features = [describe_batch(values)]
    summaries = []
    for hopping in (.35, .65, 1., 1.6, 2.5):
        matrix = np.zeros((count, length, length))
        matrix[:, sites, sites] = values
        matrix[:, sites, (sites + 1) % length] = hopping
        matrix[:, (sites + 1) % length, sites] = hopping
        energies, vectors = np.linalg.eigh(matrix)
        diagonal = np.einsum('bja,j->ba', vectors**2, phase)
        summaries.append(1 - np.mean(np.abs(diagonal)**2, axis=1))
        summaries.extend(np.quantile(np.abs(diagonal), (0, .25, .5, .75, 1), axis=1))
        participation = np.sum(vectors**4, axis=1)
        summaries.extend([participation.mean(axis=1), participation.std(axis=1), participation.max(axis=1)])
    features.append(np.column_stack(summaries))
    return np.column_stack(features)
