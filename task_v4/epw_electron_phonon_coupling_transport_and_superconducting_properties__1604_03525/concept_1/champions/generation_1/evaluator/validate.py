import json
from pathlib import Path
import numpy as np
from scipy.linalg import solve_triangular
from metrics import case_metrics, covariance, forward, properties, summarize


ROOT = Path(__file__).resolve().parents[1]


def main():
    target = json.loads((ROOT / 'evaluator/target.json').read_text())
    with np.load(ROOT / 'evaluator/hidden/test_input.npz') as archive:
        inputs = dict(archive)
    with np.load(ROOT / 'evaluator/hidden/test_labels.npz') as archive:
        labels = dict(archive)
    truth = labels['alpha2f']
    family = labels['family']
    omega = inputs['omega_mev']
    width = inputs['domega_mev']
    clean = forward(truth, inputs)
    whitened = []
    independent = []
    for row in range(len(truth)):
        expected = []
        for frequency in inputs['nu_mev'][row]:
            expected.append(sum(2 * float(width[index]) * float(truth[row, index]) * float(omega[index]) /
                                (float(omega[index]) ** 2 + float(frequency) ** 2) for index in range(len(omega))))
        assert np.allclose(expected, clean[row], rtol=1e-12, atol=1e-12)
        slots = np.flatnonzero(inputs['mask'][row])
        assert 30 <= len(slots) <= 40 and inputs['mask'][row, 0]
        root = np.linalg.cholesky(covariance(inputs, row, slots))
        whitened.extend(solve_triangular(root, inputs['interaction'][row, slots] - clean[row, slots], lower=True))
        independent.append(len(slots))
    oracle = summarize(truth, truth, family, inputs, target)
    assert oracle['core_score'] > 99.999999 and oracle['worst_family_score'] > 99.999999
    mass = 2 * width * truth / omega
    assert np.all((mass.sum(axis=1) >= 0.55 - 1e-10) & (mass.sum(axis=1) <= 2.4 + 1e-10))
    assert np.all(truth >= 0) and np.all(np.isfinite(truth))
    assert np.array_equal(np.bincount(family), np.full(4, 96))
    assert np.isclose(np.mean(np.square(whitened)), 1, atol=0.1)
    permutation = np.random.default_rng(71).permutation(len(truth))
    moved = {key: value[permutation] if value.ndim and value.shape[0] == len(truth) else value for key, value in inputs.items()}
    permuted = summarize(truth[permutation], truth[permutation], family[permutation], moved, target)
    assert np.isclose(permuted['core_score'], oracle['core_score'])
    wrong = summarize(2 * truth, truth, family, inputs, target)
    assert wrong['core_score'] < target['core_score_min']
    point = np.zeros_like(truth[:1])
    chosen = 42
    point[0, chosen] = 0.9 * omega[chosen] / (2 * width[chosen])
    coupling, _, log_frequency, rms_frequency, _ = properties(point, omega, width, inputs['mu_star'][:1])
    assert np.allclose([coupling[0], log_frequency[0], rms_frequency[0]], [0.9, omega[chosen], omega[chosen]])
    rejected = 0
    for bad in [np.zeros_like(truth), -truth, np.full_like(truth, np.nan), truth[:, :-1]]:
        try:
            summarize(bad, truth, family, inputs, target)
        except ValueError:
            rejected += 1
    assert rejected == 4
    report = {'valid': True, 'independent_forward_rows': len(truth), 'noise_whitened_mean_square': float(np.mean(np.square(whitened))),
              'oracle_label_score': oracle['core_score'], 'wrong_amplitude_score': wrong['core_score'],
              'invalid_outputs_rejected': rejected, 'permutation_invariance': True, 'single_mode_moments': True,
              'identifiability': '40 noisy observations cannot uniquely determine 192 bins. Scoring uses physical transport distances and statistical held-out recovery. Target achievability is not implied by oracle-label scoring.',
              'solvability_demonstrated': False}
    (ROOT / 'adversary/evaluator_validation.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report), flush=True)


if __name__ == '__main__':
    main()
