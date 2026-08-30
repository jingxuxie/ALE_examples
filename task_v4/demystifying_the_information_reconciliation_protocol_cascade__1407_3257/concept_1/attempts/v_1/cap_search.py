import copy
import json
from experiment import OUTPUT,size


def cap_policy(base,cap=.125,guard=False):
    policy=copy.deepcopy(base)
    caps=[]
    for frame_bits in [1024,2048,4096,8192]:
        caps.append(dict(when=[['pass_index','ge',1],['pass_index','le',1],['latency','le',.001],
                               ['frame_bits','ge',frame_bits],['frame_bits','le',frame_bits],['first_size','ge',frame_bits/8]],
                         action=dict(size=size('frame',cap))))
    rules=[]
    for rule in policy['rules']:
        when=rule['when']
        if guard and (['quiet_passes','lt',4] in when or ['quiet_passes','lt',5] in when):
            divisor=16 if ['quiet_passes','lt',4] in when else 64
            for frame_bits in [512,1024,2048,4096,8192]:
                conditions=[condition for condition in when if condition[0] not in {'corrected_fraction','estimate_ratio'}]
                conditions.extend([['frame_bits','ge',frame_bits],['frame_bits','le',frame_bits],['first_size','le',frame_bits/divisor]])
                rules.append(dict(when=conditions,action=rule['action']))
        else:
            rules.append(rule)
    policy['rules']=caps+rules
    return policy


if __name__ == '__main__':
    base=json.loads((OUTPUT/'refined_candidates.json').read_text())['refined']
    candidates={f'cap{cap}_guard{int(guard)}':cap_policy(base,cap,guard) for cap in [.25,.125] for guard in [False,True]}
    (OUTPUT/'cap_candidates.json').write_text(json.dumps(candidates,indent=2))
