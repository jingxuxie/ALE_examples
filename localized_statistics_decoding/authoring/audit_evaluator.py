import copy
import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def main():
    specification = importlib.util.spec_from_file_location('grading', ROOT / 'evaluator/v_01/evaluate.py')
    grading = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(grading)
    results = []
    for path in sorted((ROOT / 'evaluator/v_01/hidden').glob('case_*_expected.json')):
        truth = json.loads(path.read_text())['cases'][0]
        point_mass = copy.deepcopy(truth)
        independent = copy.deepcopy(truth)
        uniform = copy.deepcopy(truth)
        tolerant = copy.deepcopy(truth)
        for expected, point, factorized, flat in zip(truth['shots'], point_mass['shots'], independent['shots'], uniform['shots']):
            posterior = expected['logical_posterior']
            best = max(range(len(posterior)), key=posterior.__getitem__)
            point['logical_posterior'] = [float(label == best) for label in range(len(posterior))]
            marginals = [sum(value for label, value in enumerate(posterior) if label & (1 << bit))
                         for bit in range((len(posterior) - 1).bit_length())]
            distribution = []
            for label in range(len(posterior)):
                probability = 1.0
                for bit, marginal in enumerate(marginals):
                    probability *= marginal if label & (1 << bit) else 1.0 - marginal
                distribution.append(probability)
            factorized['logical_posterior'] = distribution
            flat['logical_posterior'] = [1.0 / len(posterior)] * len(posterior)
            flat['query_probability'] = {key: 0.5 for key in flat['query_probability']}
        uniform['mode_posterior'] = [1.0 / len(truth['mode_posterior'])] * len(truth['mode_posterior'])
        uniform['log_evidence'] = 0.0
        tolerant['log_evidence'] += 0.04
        results.append({'case': truth['id'],
                        'correct': grading.grade_case(truth, truth)[0],
                        'small_evidence_perturbation': grading.grade_case(tolerant, truth)[0],
                        'otherwise_correct_point_mass_logical': grading.grade_case(point_mass, truth)[0],
                        'otherwise_correct_factorized_logical': grading.grade_case(independent, truth)[0],
                        'uniform_forecast': grading.grade_case(uniform, truth)[0]})
    (ROOT / 'authoring/evaluator_audit.json').write_text(json.dumps(results, indent=2) + '\n')
    print(json.dumps(results))


if __name__ == '__main__':
    main()
