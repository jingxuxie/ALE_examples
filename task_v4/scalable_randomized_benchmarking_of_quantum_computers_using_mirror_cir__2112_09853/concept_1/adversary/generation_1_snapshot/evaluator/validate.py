import copy
import json
import os
from pathlib import Path
import sys

os.environ['OPENBLAS_NUM_THREADS'] = '1'
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'participant' / 'workspace'))
import numpy as np
import model


def probability_curve(counts, halfdepths=4):
    distribution = np.zeros(256)
    distribution[0] = 1
    indices = np.arange(256)
    rows = counts / 3000.0
    rows[:, 0] = 0.98
    signal = [1.0]
    for halfdepth in range(halfdepths):
        updated = np.zeros(256)
        for layer in range(32):
            intermediate = np.zeros(256)
            for pauli in np.flatnonzero(rows[layer]):
                intermediate += rows[layer, pauli] * distribution[indices ^ pauli]
            permuted = np.zeros(256)
            permuted[model.PERMUTATIONS[model.INVERSE[layer]]] = intermediate
            combined = np.zeros(256)
            for pauli in np.flatnonzero(rows[model.INVERSE[layer]]):
                combined += rows[model.INVERSE[layer], pauli] * permuted[indices ^ pauli]
            updated += model.WEIGHTS[layer] / 40 * combined
        distribution = updated
        assert np.min(distribution) >= -1e-14
        assert abs(distribution.sum() - 1) < 2e-13
        signal.append((256 * distribution[0] - 1) / 255)
    return np.array(signal)


def main():
    assertions = []
    labels = np.arange(256)
    for index, inverse in enumerate(model.INVERSE):
        assert np.array_equal(model.PERMUTATIONS[inverse, model.PERMUTATIONS[index]], labels)
    assertions.append('Every native layer has the declared inverse on all 256 Paulis.')
    ideal = np.zeros((255, 255))
    for index in range(32):
        ideal[np.arange(255), model.PERMUTATIONS[index, 1:] - 1] += model.WEIGHTS[index] / 40
    assert np.max(abs(ideal - ideal.T)) < 1e-15
    gap = float(1 - np.linalg.eigvalsh(ideal)[-2])
    assert abs(gap - 0.0698264005) < 1e-9
    assertions.append('Fixed inverse-symmetric ensemble is irreducibly mixing, gap independently diagonalized.')
    baseline = model.baseline()
    baseline_counts = model.check_constraints(baseline)
    comparison = probability_curve(baseline_counts)
    trace = model.exact_curve(baseline_counts)
    assert np.max(abs(comparison - trace[:5])) < 3e-13
    assertions.append('XOR convolution of physical Pauli probabilities agrees with PTM recursion through depth 8.')
    assert abs(trace[1] - 0.9603357281045751) < 2e-14
    baseline_result = model.evaluate(baseline)
    assert baseline_result['admissible'] and not baseline_result['passed']
    assert abs(baseline_result['relative_bias'] - 0.02051317) < 1e-7
    assertions.append('Runnable baseline is admissible and fails the predeclared bias target.')
    mutations = []
    for value in [True, 20.0, float('nan'), 10 ** 80, -1]:
        artifact = copy.deepcopy(baseline)
        artifact['single'][0][0][0] = value
        mutations.append(artifact)
    mutations.extend([{}, {'single': [], 'cx': []}, {'single': baseline['single'], 'cx': []}])
    for artifact in mutations:
        assert not model.evaluate(artifact)['admissible']
    perturbed = copy.deepcopy(baseline)
    perturbed['single'][0][0][0] += 1
    perturbed['single'][0][0][1] -= 1
    assert not model.evaluate(perturbed)['admissible']
    assertions.append('Malformed, noninteger, nonfinite, out-of-range, and calibration-breaking artifacts rejected.')
    shape = 0.987 * np.exp(-0.017 * model.DEPTHS)
    recovered = model.fit_curve(shape)
    assert abs(recovered['decay'] - 0.017) < 1e-9
    assert recovered['max_residual'] < 1e-8
    assertions.append('Least-squares fitter recovers a synthetic exact exponential.')
    witness_file = ROOT / 'adversary' / 'winning_witness.json'
    witness_result = None
    if witness_file.exists():
        witness = model.load_artifact(witness_file)
        witness_counts = model.check_constraints(witness)
        witness_result = model.evaluate(witness)
        assert witness_result['passed'], witness_result
        independent = probability_curve(witness_counts)
        assert np.max(abs(independent - model.exact_curve(witness_counts)[:5])) < 3e-13
        assert abs(independent[1] - comparison[1]) < 3e-13
        assertions.append('Privileged integer witness passes, with independent probability-channel confirmation.')
    result = {'passed': True, 'checks': assertions, 'ideal_mixing_gap': gap,
              'baseline': baseline_result, 'privileged_witness': witness_result,
              'max_independent_curve_difference': float(np.max(abs(comparison - trace[:5])))}
    (ROOT / 'evaluator' / 'hidden' / 'validation.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
