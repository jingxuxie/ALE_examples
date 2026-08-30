import copy
import json

from experiment import OUTPUT, load_suite, make_policy, run_candidates, size
from stopping_search import stopped_policy


def candidates():
    policies = {}
    for first in [.75,1,1.25,1.5]:
        base = stopped_policy(make_policy(first=('estimate',first),second=('remaining',1),third=('frame',.5)),6)
        policies[f'first{first}_remaining1'] = base
        parity = copy.deepcopy(base)
        parity['schedule'][1]['size'] = size('parity',3)
        policies[f'first{first}_parity3'] = parity
        for factor in [.5,1,2,4]:
            policy = copy.deepcopy(base)
            policy['rules'].append(dict(when=[['pass_index','ge',1],['pass_index','lt',2],['last_odd_fraction','ge',.45]],
                                       action=dict(size=size('first',factor))))
            policies[f'first{first}_saturated{factor}'] = policy
        policy = copy.deepcopy(base)
        for action in policy['schedule']:
            action['batch'] = 'pass'
        policies[f'first{first}_batchpass'] = policy
    return policies


if __name__ == '__main__':
    policies = candidates()
    (OUTPUT / 'adaptation_candidates.json').write_text(json.dumps(policies,indent=2))
    run_candidates(policies,load_suite('independent',frames=4),tag='adaptation_small')
