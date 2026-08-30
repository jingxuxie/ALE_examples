import json
from experiment import make_policy, OUTPUT


def broader():
    candidates = {}
    for first in [.75, 1, 1.25, 1.5, 2]:
        for basis, second in [('parity', 2), ('parity', 3), ('parity', 4), ('parity', 6), ('remaining', 1), ('remaining', 2), ('remaining', 4)]:
            name = f'est{first}_{basis}{second}'
            candidates[name] = make_policy(first=('estimate', first), second=(basis, second))
    return candidates


if __name__ == '__main__':
    (OUTPUT / 'broader_candidates.json').write_text(json.dumps(broader()))
    previous = json.loads((OUTPUT / 'initial_policies.json').read_text())
    selected = ['estimate0.5_parity2_smallest', 'estimate0.75_parity2_smallest', 'paper_first1_parity2_smallest',
                'estimate0.75_parity4_smallest', 'paper_first1_parity4_smallest']
    (OUTPUT / 'early_dev_candidates.json').write_text(json.dumps({name:previous[name] for name in selected}))
