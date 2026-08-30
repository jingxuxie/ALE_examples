import os
os.environ['OPENBLAS_NUM_THREADS'] = '1'
os.environ['OMP_NUM_THREADS'] = '1'
import json
import numpy as np
from scipy.linalg import expm
from scipy.special import expit
from search import ROOT, NAMES, baseline, load_instances


def unique_keys(pairs):
    result = {}
    for key, value in pairs:
        assert key not in result
        result[key] = value
    return result


path = ROOT / 'submission.json'
assert path.is_file() and not path.is_symlink() and path.stat().st_size <= 32768
artifact = json.loads(path.read_text(), object_pairs_hook=unique_keys, parse_constant=lambda value: (_ for _ in ()).throw(ValueError(value)))
assert set(artifact) == {'schema_version', 'stages'} and artifact['schema_version'] == 1
stages = artifact['stages']
assert len(stages) == 33 and all(set(stage) == {'component', 'coefficient'} for stage in stages)
assert all(type(stage['coefficient']) in [float, int] for stage in stages)
word = np.array([NAMES.index(stage['component']) for stage in stages])
values = np.array([stage['coefficient'] for stage in stages])
assert np.all(np.isfinite(values)) and values.min() >= 1e-5 and values.max() <= 1
assert np.all(word == word[::-1]) and np.all(word[:-1] != word[1:])
assert np.max(abs(values - values[::-1])) <= 1e-12
assert np.max(abs(np.bincount(word, weights=values, minlength=5) - 1)) <= 1e-10
values = (values + values[::-1]) / 2
baseline_word, baseline_values = baseline()
ratios = []
for identity, family, matrices in load_instances():
    total = matrices.sum(axis=0)
    eigenvalues, eigenvectors = np.linalg.eigh(total)
    instance_ratios = []
    for step in [.4, .6, .8, 1.]:
        approximations = []
        for current_word, current_values in [(word, values), (baseline_word, baseline_values)]:
            left = np.eye(len(total), dtype=complex)
            for index in range(17):
                left = left @ expm(step * current_values[index] * (.5 if index == 16 else 1.) * matrices[current_word[index]])
            vectors, singular, _ = np.linalg.svd(left)
            approximations.append((left @ left.conj().T, vectors, 2 * np.log(singular)))
        for repetitions in [1, 4]:
            exact_prop = expm(repetitions * step * total)
            exact_green = (eigenvectors * expit(-repetitions * step * eigenvalues)) @ eigenvectors.conj().T
            errors = []
            for product, vectors, logarithms in approximations:
                prop_error = np.linalg.norm(np.linalg.matrix_power(product, repetitions) - exact_prop) / np.linalg.norm(exact_prop)
                approx_green = (vectors * expit(-repetitions * logarithms)) @ vectors.conj().T
                green_error = np.linalg.norm(approx_green - exact_green) / np.linalg.norm(exact_green)
                errors.append([prop_error, green_error])
            instance_ratios.extend(np.maximum(errors[0], 1e-14) / np.maximum(errors[1], 1e-14))
    ratios.append(instance_ratios)
ratios = np.array(ratios)
family_scores = 1 / np.sqrt(np.mean(ratios.reshape(8, -1) ** 2, axis=1))
report = {'structurally_valid': True, 'core_score': float(np.exp(np.mean(np.log(family_scores)))), 'worst_family_score': float(family_scores.min()), 'maximum_pointwise_error_ratio': float(ratios.max()), 'family_scores': family_scores.tolist()}
report['public_targets_pass'] = report['core_score'] >= 1.8 and report['worst_family_score'] >= 1.35 and report['maximum_pointwise_error_ratio'] <= 1
(ROOT / 'independent_report.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report, indent=2), flush=True)
