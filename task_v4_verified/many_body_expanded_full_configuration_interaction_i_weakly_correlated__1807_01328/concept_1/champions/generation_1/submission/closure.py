import numpy as np

from experiment import MASKS, ORDERS, SUBSETS, report, transform


def closure_features(terms, mean, queries, observed):
    first = -np.sum(terms[MASKS[1]])
    second = terms[MASKS[2]].sum()
    third = terms[MASKS[3]].sum()
    second_abs = np.abs(terms[MASKS[2]]).sum()
    third_abs = np.abs(terms[MASKS[3]]).sum()
    fourth = observed.sum()
    fourth_abs = np.abs(observed).sum()
    ratio = third_abs / max(first, 1e-12)
    pair_ratio = second_abs / max(first, 1e-12)
    known = np.isin(MASKS[4], queries)
    strength = SUBSETS[MASKS[4]][:, MASKS[3]] @ np.abs(terms[MASKS[3]])
    missing_ratio = np.sum(strength[~known] ** 2) / max(np.sum(strength[known] ** 2), 1e-20)
    predicted_fourth = mean[MASKS[4][~known]].sum()
    predicted_fifth = mean[ORDERS >= 5].sum()
    return np.array([predicted_fourth, predicted_fifth, third * ratio, second * ratio,
                     fourth * pair_ratio, fourth * ratio, third * pair_ratio ** 2,
                     np.sum(terms[MASKS[3]] ** 2) / max(first, 1e-12),
                     fourth * missing_ratio, fourth_abs * ratio, third_abs * ratio,
                     predicted_fourth * pair_ratio, predicted_fifth * pair_ratio])


def main():
    data = np.load('train.npz')
    terms = transform(data['energies'][-1800:])
    families = data['families'][-1800:]
    means = np.zeros_like(terms)
    for order in [4, 5]:
        prediction = np.load('neural_validation' + str(order) + '.npz')
        means[:, prediction['masks']] = prediction['predicted']
    means[(families == 0) | (families == 3) | (families == 4)] = 0
    rows, targets = [], []
    for row, mean in zip(terms, means):
        strength = SUBSETS[MASKS[4]][:, MASKS[3]] @ np.abs(row[MASKS[3]])
        queries = MASKS[4][np.argsort(-strength, kind='stable')[:26]]
        observed = row[queries]
        rows.append(closure_features(row, mean, queries, observed))
        targets.append(row[ORDERS >= 4].sum() - observed.sum())
    rows, targets = np.array(rows), np.array(targets)
    for ridge in [.1, 1, 10, 100]:
        errors = np.zeros(len(terms))
        coefficients = []
        for family in range(6):
            train = (families == family) & (np.arange(len(terms)) < 1200)
            selected = families == family
            scale = np.maximum(np.sqrt(np.mean(rows[train] ** 2, axis=0)), 1e-8)
            matrix = rows[train] / scale
            weights = np.linalg.solve(matrix.T @ matrix + ridge * np.eye(matrix.shape[1]), matrix.T @ targets[train]) / scale
            coefficients.append(weights)
            errors[selected] = rows[selected] @ weights - targets[selected]
        report(errors[1200:], families[1200:], str(ridge))
        np.savez('closure' + str(ridge) + '.npz', weights=coefficients)
    np.savez('closure_data.npz', inputs=rows, targets=targets, families=families)


if __name__ == '__main__':
    main()
