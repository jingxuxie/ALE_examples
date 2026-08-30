import os
os.environ['OPENBLAS_NUM_THREADS'] = '1'
os.environ['OMP_NUM_THREADS'] = '1'
os.environ['MKL_NUM_THREADS'] = '1'
import argparse
import json
import math
from pathlib import Path
import numpy as np
from scipy.linalg import expm
from search import ROOT, INPUT, SPEC, NAMES, FAMILIES, baseline, matrices, generate, evaluate, load

def strict_object(pairs):
    result = {}
    for key, value in pairs:
        assert key not in result, 'Duplicate JSON key'
        result[key] = value
    return result

def structure(path):
    assert path.is_file() and not path.is_symlink()
    assert path.stat().st_size <= 32768
    payload = json.loads(path.read_text(), object_pairs_hook=strict_object)
    assert set(payload) == {'schema_version', 'stages'}
    assert type(payload['schema_version']) is int and payload['schema_version'] == 1
    stages = payload['stages']
    assert len(stages) == 33
    totals = dict.fromkeys(NAMES, 0.0)
    for index, stage in enumerate(stages):
        assert set(stage) == {'component','coefficient'}
        component, coefficient = stage['component'], stage['coefficient']
        assert component in NAMES
        assert type(coefficient) in (int,float) and math.isfinite(coefficient)
        assert 0.00001 <= coefficient <= 1
        assert component == stages[32-index]['component']
        assert abs(coefficient-stages[32-index]['coefficient']) <= 1e-12
        if index:
            assert component != stages[index-1]['component']
        totals[component] += coefficient
    assert max(abs(total-1) for total in totals.values()) <= 1e-10
    return dict(stage_count=len(stages),component_sums=totals,
                minimum_coefficient=min(stage['coefficient'] for stage in stages),
                maximum_coefficient=max(stage['coefficient'] for stage in stages),bytes=path.stat().st_size)

def full_exponential_evaluation(instances, word, coeff):
    baseword, basecoeff = baseline()
    ratios = [[] for family in FAMILIES]
    worst = (0,None)
    for instance in instances:
        ham = matrices(instance)
        identity = np.eye(ham.shape[1])
        family = FAMILIES.index(instance['family'])
        for step in SPEC['sampling']['dtau']:
            products = []
            for schedule, weights in [(word,coeff),(baseword,basecoeff)]:
                result = identity.astype(complex)
                for index in list(range(17))+list(range(15,-1,-1)):
                    result = result @ expm(-step*weights[index]*ham[schedule[index]])
                products.append(result)
            for repeat in SPEC['sampling']['repetitions']:
                exact = expm(-step*repeat*ham.sum(axis=0))
                exact_green = np.linalg.inv(identity+exact)
                errors = []
                for result in products:
                    power = np.linalg.matrix_power(result,repeat)
                    green = np.linalg.inv(identity+power)
                    errors.append([np.linalg.norm(power-exact)/np.linalg.norm(exact),
                                   np.linalg.norm(green-exact_green)/np.linalg.norm(exact_green)])
                point = np.maximum(errors[0],1e-14)/np.maximum(errors[1],1e-14)
                ratios[family].extend(point.tolist())
                if max(point)>worst[0]:
                    worst = (float(max(point)),(instance['id'],step,repeat,point.tolist()))
    scores = [float(1/np.sqrt(np.mean(np.square(points)))) for points in ratios]
    return dict(scores=dict(zip(FAMILIES,scores)),core=float(np.prod(scores)**0.25),
                worst_family=min(scores),max_ratio=worst[0],worst_point=worst[1])

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--source',default='best.json')
    parser.add_argument('--count',type=int,default=500)
    parser.add_argument('--seed',type=int,default=836189)
    args = parser.parse_args()
    snapshot = ROOT/'candidate.json'
    snapshot.write_text((ROOT/args.source).read_text())
    report = {'structure':structure(snapshot)}
    word,coeff = load(snapshot)
    training = json.loads((INPUT/'training_instances.json').read_text())['instances']
    report['public_training_scipy_expm'] = full_exponential_evaluation(training,word,coeff)
    print('PUBLIC INDEPENDENT EXPM',json.dumps(report['public_training_scipy_expm'],indent=2),flush=True)
    report['generated_instances'] = 4*args.count
    report['generated_seed'] = args.seed
    report['generated_validation'] = evaluate(generate(args.count,args.seed),word,coeff)
    for section in ['public_training_scipy_expm','generated_validation']:
        result = report[section]
        assert result['core'] >= 1.50
        assert result['worst_family'] >= 1.20
        assert result['max_ratio'] <= 1.15
    (ROOT/'submission.json').write_text(snapshot.read_text())
    report['submission_structure'] = structure(ROOT/'submission.json')
    (ROOT/'validation_report.json').write_text(json.dumps(report,indent=2)+'\n')
    print('VALIDATED SUBMISSION',ROOT/'submission.json',flush=True)

if __name__ == '__main__':
    main()
