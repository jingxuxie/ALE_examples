import json
from experiment import OUTPUT, load_suite, make_policy, run_candidates
from stopping_search import stopped_policy


if __name__ == '__main__':
    cases = []
    reference = {}
    for split, frames in [('train',None),('dev',None),('independent',4)]:
        cases.extend(case for case in load_suite(split,frames)['cases'] if case['latency']<=.001)
        reference.update(json.loads((OUTPUT/f'reference_{split}.json').read_text()))
    suite = dict(split='optimization',cases=cases,stress=[])
    (OUTPUT/'reference_optimization.json').write_text(json.dumps(reference))
    policies = {}
    for first in [.75,1,1.25,1.5,1.75,2]:
        for second in [1.5,2,2.5,3,3.5,4,5,6]:
            policies[f'first{first}_second{second}'] = stopped_policy(make_policy(first=('estimate',first),second=('parity',second),third=('frame',.25)),10,14)
    run_candidates(policies,suite,tag='bandwidth_grid')
