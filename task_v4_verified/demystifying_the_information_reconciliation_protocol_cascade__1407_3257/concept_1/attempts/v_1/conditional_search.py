import copy
from experiment import load_suite, make_policy, run_candidates, size
from stopping_search import stopped_policy


policies = {}
for first in [1,1.25]:
    base = stopped_policy(make_policy(first=('estimate',first),third=('frame',.5)),6,14)
    policies[f'first{first}_paper'] = base
    for threshold in [.4,.5]:
        for factor in [1,2,4]:
            policy = copy.deepcopy(base)
            policy['rules'].append(dict(when=[['pass_index','ge',1],['pass_index','lt',2],['last_odd_fraction','ge',threshold]],
                                       action=dict(size=size('first',factor))))
            policies[f'first{first}_odd{threshold}_factor{factor}'] = policy

if __name__ == '__main__':
    run_candidates(policies,load_suite('independent',frames=4),tag='conditional_small')
