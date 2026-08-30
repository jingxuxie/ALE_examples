import sys,random,time,json
sys.path.insert(0, '/tmp/cascade-c3-g2-v2-0f0el7m5/participant/input')
from simulator import Device
import policy_v5
from policy_v11 import LocalModel
class ExtendedModel(LocalModel):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, source_limit=6, **kwargs)
policy_v5.LocalModel = ExtendedModel
rng=random.Random(994185)
cases=[dict(family=('RR','RS','SS')[index%3],contamination_denominator=(8,6,4)[index//3%3],seed=rng.getrandbits(128)) for index in range(90)]
failures=[int(line.split()[0]) for line in open('fresh_v5.txt') if line.rstrip().endswith('WRONG')]
for index in failures + [index for index in range(24) if index not in failures]:
    case=cases[index]
    device=Device(case['family'],case['contamination_denominator'],case['seed'])
    policy=policy_v5.Policy(device.handle)
    started=time.process_time()
    result=policy.run()
    refined=[model.refine_full() for model in policy.models]
    left,right=refined
    scores=[left*right,left*(1-right)+(1-left)*right,(1-left)*(1-right)]
    family=('RR','RS','SS')[max(range(3),key=scores.__getitem__)]
    print(index,case['family'],case['contamination_denominator'],result[0],family,[round(value,4) for value in result[1][:2]],[round(value,4) for value in refined],round(time.process_time()-started,3), 'OK' if case['family']==family else 'WRONG',flush=True)
