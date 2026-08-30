import copy
import json
from experiment import OUTPUT,size
from cap_search import cap_policy


def first_cap(base,divisor=8):
    policy=copy.deepcopy(base)
    rules=[]
    for frame_bits in [1024,2048,4096,8192]:
        rules.append(dict(when=[['pass_index','le',0],['latency','le',.001],['frame_bits','ge',frame_bits],
                               ['frame_bits','le',frame_bits],['first_size','ge',frame_bits/divisor]],
                         action=dict(size=size('frame',1/divisor))))
    policy['rules']=rules+policy['rules']
    return policy


if __name__ == '__main__':
    base=json.loads((OUTPUT/'refined_candidates.json').read_text())['refined']
    guarded=cap_policy(base,.5,True)
    guarded['rules']=guarded['rules'][4:]
    candidates={
        'first_cap8':first_cap(base),
        'first_cap8_guard':first_cap(guarded),
        'both_cap8_guard':first_cap(cap_policy(base,.125,True)),
        'first_cap16_guard':first_cap(guarded,16),
    }
    (OUTPUT/'first_cap_candidates.json').write_text(json.dumps(candidates,indent=2))
