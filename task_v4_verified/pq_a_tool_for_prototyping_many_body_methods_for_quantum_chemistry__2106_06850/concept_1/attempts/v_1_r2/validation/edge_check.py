import json

import numpy as np

from benchmark import REPORTS, validate
from solve import solve


def main():
    case = {'dimensions': {'o': 4, 'v': 12},
            'index_types': dict.fromkeys('abcd', 'o') | dict.fromkeys('AB', 'v'),
            'tensors': {'X': ['o', 'v'], 'Y': ['v', 'o'], 'Z': ['o', 'o'],
                        'S': [], 'intermediate_0': ['o']},
            'memory_cap': 100000,
            'terms': [
                {'inputs': [['X', 'aB'], ['Y', 'Bc'], ['Z', 'cd']], 'output': 'ad'},
                {'inputs': [['Z', 'cd'], ['X', 'bA'], ['Y', 'Ac']], 'output': 'db'},
                {'inputs': [['X', 'aB'], ['Y', 'Bc'], ['Z', 'ad']], 'output': 'cd'},
                {'inputs': [['Z', 'ab'], ['Z', 'bc'], ['Z', 'cd']], 'output': 'abcd'},
                {'inputs': [['S', ''], ['X', 'aB'], ['Y', 'Bc']], 'output': 'ac'},
                {'inputs': [['S', '']] * 3, 'output': ''},
                {'inputs': [['S', '']] * 5, 'output': ''},
                {'inputs': [['S', '']] * 6, 'output': ''},
                {'inputs': [['intermediate_0', 'a'], ['S', ''], ['S', '']], 'output': ''},
                {'inputs': [['intermediate_0', 'a'], ['intermediate_0', 'b'],
                            ['intermediate_0', 'c']], 'output': 'abc'},
                {'inputs': [['intermediate_0', 'a'], ['intermediate_0', 'a'],
                            ['intermediate_0', 'b']], 'output': 'b'},
                {'inputs': [['intermediate_0', 'a'], ['intermediate_0', 'a'], ['S', '']], 'output': 'a'}]}
    plan = solve(case)
    result = validate(case, plan)
    generator = np.random.default_rng(9312)
    inputs = {name: generator.normal(size=tuple(case['dimensions'][kind] for kind in kinds))
              for name, kinds in case['tensors'].items()}
    live = dict(inputs)
    for step in plan['steps']:
        if 'delete' in step:
            del live[step['delete']]
        elif 'id' in step:
            expression = ','.join(axes for name, axes in step['inputs']) + '->' + step['output']
            live[step['id']] = np.einsum(expression, *(live[name] for name, axes in step['inputs']))
        else:
            term = case['terms'][step['emit']]
            expression = ','.join(axes for name, axes in term['inputs']) + '->' + term['output']
            expected = np.einsum(expression, *(inputs[name] for name, axes in term['inputs']))
            name, axes = step['input']
            actual = np.einsum(axes + '->' + step['output'], live[name])
            np.testing.assert_allclose(actual, expected, rtol=1e-11, atol=1e-11)
    result['numerical_checks'] = len(case['terms'])
    (REPORTS / 'edge_results.json').write_text(json.dumps(result, indent=2))
    print(json.dumps(result), flush=True)


if __name__ == '__main__':
    main()
