import argparse
import hashlib
import json
from pathlib import Path
import sys
import numpy as np

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from build_package import ROOT, put
from oracle import geometric, dak_crosscheck


def make_cases(seed=83174629, size=12):
    rng = np.random.default_rng(seed)
    cases = []
    def unit():
        vector = rng.normal(size=3)
        return vector/np.linalg.norm(vector)
    for family in ['generic','soft','double_collinear','triple_collinear','radiator_collinear','rotation','relabel','scale']:
        for number in range(size):
            angle = 10.**(-2-(number%9)*1.2)
            soft = 10.**(-3-(number%8)*1.8)
            first_axis = unit()
            second_axis = unit()
            while np.dot(first_axis,second_axis) > .5:
                second_axis = unit()
            def near(axis):
                tangent = unit()
                tangent -= tangent.dot(axis)*axis
                tangent /= np.linalg.norm(tangent)
                return axis*np.cos(angle)+tangent*np.sin(angle)
            spatial = [.9*first_axis,.3*unit(),.4*unit(),.8*second_axis]
            limit = None
            bound = None
            if family == 'soft':
                spatial[1] *= soft
                spatial[2] *= soft
                bound = 20*soft+5e-10
            if family == 'double_collinear':
                spatial[1] = .3*near(first_axis)
                spatial[2] = .4*near(second_axis)
                bound = 20*angle+5e-10
            if family == 'triple_collinear':
                spatial[1] = .3*near(first_axis)
                spatial[2] = .4*near(first_axis)
                bound = 20*angle+5e-10
            if family == 'radiator_collinear':
                angle = 10.**(-2-(number%8)*1.05)
                spatial[1] = .3*near(first_axis)
                spatial[2] = .4*second_axis
                spatial[3] = .8*near(first_axis)
            spatial.append(-sum(spatial))
            momenta = np.array([list(vector)+[np.linalg.norm(vector)] for vector in spatial])
            momenta /= momenta[:,3].sum()
            if family == 'soft':
                limit = momenta[[0,3]].copy()
            elif family == 'double_collinear':
                limit = np.array([momenta[0]+momenta[1],momenta[2]+momenta[3]])
            elif family == 'triple_collinear':
                limit = np.array([momenta[0]+momenta[1]+momenta[2],momenta[3]])
            labels = [1,2,3,4,5]
            slots = [1,2,3]
            if family == 'relabel':
                labels = list(map(int,rng.permutation(5)+1))
                slots = list(map(int,rng.permutation(3)+1))
            scale = 10.**([-90,-40,-10,0,10,40,90][number%7]) if family == 'scale' else 1.
            momenta *= scale
            axis = np.r_[unit(),1.]
            if family == 'rotation':
                axes = [[1e-200,1,1e-200,1],[1,1e-200,-1e-200,1],[0,-1,1e-200,1],
                        [1e-200,-1,-1e-200,1],[0,0,-1,1],[0,0,1,1]]
                axis = np.asarray(axes[number%6]) * 10.**([-70,0,70][number%3])
            case = {'id': f'{family}-{number:03d}', 'family': family, 'p':momenta.tolist(),
                    'labels':labels,'slots':slots,'axis':axis.tolist()}
            if limit is not None:
                case['limit'] = (limit*scale).tolist()
                case['limit_bound'] = bound
            cases.append(case)
    for number in range(min(size,8)):
        original = cases[number]
        orthogonal, _ = np.linalg.qr(rng.normal(size=(3,3)))
        if np.linalg.det(orthogonal)<0:
            orthogonal[:,0] *= -1
        permutation = rng.permutation(5)
        scale = 10.**(number%5*20-40)
        momenta = np.array(original['p'])
        momenta[:,:3] = momenta[:,:3]@orthogonal.T
        momenta = momenta[permutation]*scale
        labels = [int(np.where(permutation==index)[0][0]+1) for index in range(5)]
        case = {'id':f'metamorphic-{number:03d}','family':'metamorphic','p':momenta.tolist(),
                'labels':labels,'slots':list(map(int,rng.permutation(3)+1)),
                'axis':np.r_[unit(),1.].tolist(), 'parent': original['id'],
                'transform':orthogonal.tolist(),'scale_factor':scale}
        cases.append(case)
    return cases


def serialize(cases,repeats=1):
    lines = [f'{len(cases)} {repeats}']
    for case in cases:
        lines += [' '.join(format(value,'.17e') for value in vector) for vector in case['p']]
        lines += [' '.join(map(str,case['labels']+case['slots']))]
        lines += [' '.join(format(value,'.17e') for value in case['axis'])]
    return '\n'.join(lines)+'\n'


def generate():
    cases = make_cases()
    references = [geometric(case) for case in cases]
    cross_error = 0.
    precision_error = 0.
    for case, reference in zip(cases,references):
        energy = sum(vector[3] for vector in case['p'])
        cross_error = max(cross_error,float(np.max(np.abs(dak_crosscheck(case)-np.array(reference['mapped'])[case['slots'][0]-1]))/energy))
        higher = geometric(case,140)
        precision_error = max(precision_error,float(np.max(np.abs(np.array(higher['mapped'])-reference['mapped']))/energy))
        raw = np.array(case['p'])/energy
        assert np.max(np.abs(raw[:,:3].sum(axis=0))) < 2e-15
        assert np.max(np.abs(raw[:,3]-np.linalg.norm(raw[:,:3],axis=1))) < 2e-15
    assert cross_error < 2e-14 and precision_error < 2e-14
    put('evaluator/hidden/cases.json',json.dumps(cases,indent=2)+'\n')
    put('evaluator/hidden/references.json',json.dumps(references,indent=2)+'\n')
    put('evaluator/hidden/oracle_validation.json',json.dumps({'cases':len(cases),'geometric_vs_dak_max_error':cross_error,
        'dps90_vs_dps140_max_error':precision_error,'null_shell_and_conservation_checked_at':'1e-45',
        'all_inputs_massless_CM':True},indent=2)+'\n')
    examples = make_cases(seed=22781,size=2)
    examples = [case for case in examples if case['family'] in ['generic','soft','double_collinear','triple_collinear']]
    put('participant/input/examples.txt',serialize(examples))
    put('participant/input/examples.json',json.dumps(examples,indent=2)+'\n')
    put('participant/input/examples_expected.json',json.dumps([geometric(case) for case in examples],indent=2)+'\n')


if __name__ == '__main__':
    generate()
