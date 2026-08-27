import copy
import importlib.util
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]


def load(name, path):
    specification = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(module)
    return module


def main():
    sys.path.insert(0, str(ROOT / 'solution/v_02'))
    decoder = load('decoder_audit', ROOT / 'solution/v_02/solve.py')
    evaluator = load('evaluator_audit', ROOT / 'evaluator/v_02/evaluate.py')
    model = json.loads((ROOT / 'solution/v_02/model.json').read_text())
    independent = copy.deepcopy(model)
    independent['transition'] = [model['initial'][:] for _ in model['initial']]
    constant = copy.deepcopy(model)
    constant['slopes'] = [0.0] * len(model['slopes'])
    results = []
    for name, variant in [('independent_shot_regimes', independent), ('constant_dose_rates', constant)]:
        scores = []
        cases = []
        for path in sorted((ROOT / 'evaluator/v_02/hidden').glob('case_*.json')):
            if '_expected' in path.name:
                continue
            case = json.loads(path.read_text())['cases'][0]
            truth = json.loads(path.with_name(path.stem + '_expected.json').read_text())['cases'][0]
            predicted = decoder.decode_case(case, variant)
            score, metrics = evaluator.grade_case(predicted, truth)
            scores.append(score)
            cases.append({'id': case['id'], 'score': score, **metrics})
        results.append({'ablation': name, 'score': sum(scores) / len(scores), 'cases': cases})
    (ROOT / 'authoring/v02_ablation_audit.json').write_text(json.dumps(results, indent=2) + '\n')
    print(json.dumps([{'ablation': result['ablation'], 'score': result['score']} for result in results]))


if __name__ == '__main__':
    main()
