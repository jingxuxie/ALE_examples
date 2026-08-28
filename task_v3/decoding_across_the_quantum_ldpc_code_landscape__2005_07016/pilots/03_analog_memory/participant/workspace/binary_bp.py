import argparse
import numpy as np
import scipy.sparse as sparse


def recover(parity, probabilities, syndrome, iterations=30):
    matrix = parity.tocsr()
    columns = matrix.indices
    rows = np.repeat(np.arange(matrix.shape[0]), np.diff(matrix.indptr))
    prior = np.log((1 - probabilities) / probabilities)
    messages = prior[columns].copy()
    correction = np.zeros(matrix.shape[1], dtype=np.uint8)
    for iteration in range(iterations):
        outgoing = np.zeros_like(messages)
        for check in range(matrix.shape[0]):
            start, stop = matrix.indptr[check:check + 2]
            incoming = messages[start:stop]
            if len(incoming) == 0:
                continue
            signs = np.where(incoming < 0, -1.0, 1.0)
            magnitudes = np.abs(incoming)
            minimum_index = np.argmin(magnitudes)
            minimum = magnitudes[minimum_index]
            second = np.partition(magnitudes, 1)[1] if len(incoming) > 1 else 40.0
            values = np.full(len(incoming), minimum)
            values[minimum_index] = second
            outgoing[start:stop] = 0.625 * ((-1) ** int(syndrome[check])) * np.prod(signs) * signs * values
        posterior = prior + np.bincount(columns, weights=outgoing, minlength=matrix.shape[1])
        correction = (posterior < 0).astype(np.uint8)
        if np.array_equal(matrix @ correction % 2, syndrome):
            break
        messages = np.clip(posterior[columns] - outgoing, -40, 40)
    return correction


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', required=True)
    parser.add_argument('--output', required=True)
    arguments = parser.parse_args()
    case = np.load(arguments.input, allow_pickle=False)
    parity = sparse.coo_matrix((np.ones(len(case['h_rows']), dtype=np.uint8), (case['h_rows'], case['h_cols'])), shape=tuple(case['h_shape'])).tocsr()
    corrections = np.array([recover(parity, case['priors'], syndrome) for syndrome in case['syndromes']], dtype=np.uint8)
    np.savez_compressed(arguments.output, corrections=corrections)


if __name__ == '__main__':
    main()
