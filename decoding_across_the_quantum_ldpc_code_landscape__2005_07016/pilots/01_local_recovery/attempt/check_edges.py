import numpy as np
import scipy.sparse as sp
from pathlib import Path

from validate import native_decode, row_basis, in_span


def main():
    rng = np.random.default_rng(83717)
    for checks, variables in [(0, 0), (0, 20), (10, 0), (1, 1), (8, 16), (40, 100)]:
        dense = (rng.random((checks, variables)) < .2).astype(np.uint8)
        parity = sp.csr_matrix(dense)
        priors = rng.uniform(0, 1, variables)
        if variables:
            priors[::4] = 0
            priors[1::4] = 1
            priors[2::4] = .5
        actual = (rng.random((100, variables)) < priors).astype(np.uint8)
        syndromes = (parity @ actual.T).T % 2
        answer, elapsed, stats = native_decode(parity, priors, syndromes)
        assert answer.shape == actual.shape
        assert np.all((answer == 0) | (answer == 1))
        assert np.array_equal((parity @ answer.T).T % 2, syndromes)
        if checks == 0:
            assert np.all(answer == (priors > .5))
        print('edge case', checks, variables, 'passed', flush=True)

    for trial in range(30):
        checks = int(rng.integers(2, 40))
        variables = int(rng.integers(2, 100))
        dense = (rng.random((checks, variables)) < rng.uniform(.03, .3)).astype(np.uint8)
        dense = np.hstack([dense, dense[:, :variables // 2], np.zeros((checks, 3), dtype=np.uint8)])
        dense = np.vstack([dense, dense[:2], dense[0] ^ dense[1]])
        dense = dense[rng.permutation(len(dense))][:, rng.permutation(dense.shape[1])]
        parity = sp.csr_matrix(dense)
        priors = rng.uniform(.001, .3, parity.shape[1])
        actual = (rng.random((25, parity.shape[1])) < priors).astype(np.uint8)
        syndromes = (parity @ actual.T).T % 2
        answer, elapsed, stats = native_decode(parity, priors, syndromes)
        assert np.array_equal((parity @ answer.T).T % 2, syndromes), trial
    print('750 randomized rank-deficient/permuted/duplicate shots passed', flush=True)

    parity = sp.hstack([sp.csr_matrix(np.ones((100, 1), dtype=np.uint8)), sp.eye(100, dtype=np.uint8)], format='csr')
    priors = np.concatenate([[0.], np.full(100, .1)])
    syndromes = np.ones((1, 100), dtype=np.uint8)
    answer, elapsed, stats = native_decode(parity, priors, syndromes)
    assert answer[0, 0] == 0 and np.all(answer[0, 1:] == 1)
    print('zero-probability alternatives correctly excluded from finite-likelihood recovery', flush=True)

    checks, variables = 8, 16
    dense = (rng.random((checks, variables)) < .35).astype(np.uint8)
    parity = sp.csr_matrix(dense)
    priors = rng.uniform(.02, .14, variables)
    all_errors = ((np.arange(1 << variables)[:, None] >> np.arange(variables)) & 1).astype(np.uint8)
    all_syndromes = all_errors @ dense.T % 2
    indices = all_syndromes.astype(np.int64) @ (1 << np.arange(checks))
    costs = all_errors @ np.log((1 - priors) / priors)
    optimum = np.full(1 << checks, np.inf)
    np.minimum.at(optimum, indices, costs)
    actual = (rng.random((300, variables)) < priors).astype(np.uint8)
    syndromes = (parity @ actual.T).T % 2
    answer, elapsed, stats = native_decode(parity, priors, syndromes)
    assert np.array_equal((parity @ answer.T).T % 2, syndromes)
    decoded_cost = answer @ np.log((1 - priors) / priors)
    optimal_cost = optimum[syndromes.astype(np.int64) @ (1 << np.arange(checks))]
    print('exhaustive likelihood optimum:', int(np.isclose(decoded_cost, optimal_cost).sum()), '/ 300', flush=True)
    assert np.isclose(decoded_cost, optimal_cost).mean() > .9

    example_path = Path(__file__).resolve().parent.parent / 'participant' / 'input' / 'example.npz'
    if not example_path.exists():
        return
    with np.load(example_path, allow_pickle=False) as example:
        parity = sp.coo_matrix((np.ones(len(example['h_rows']), dtype=np.uint8), (example['h_rows'], example['h_cols'])), shape=tuple(example['h_shape'])).tocsr()
        basis = row_basis(parity.T)
        feasible = [in_span(syndrome, basis) for syndrome in example['syndromes']]
        print('supplied example feasible syndrome rows:', np.flatnonzero(feasible).tolist(), '/', len(feasible), flush=True)


if __name__ == '__main__':
    main()
