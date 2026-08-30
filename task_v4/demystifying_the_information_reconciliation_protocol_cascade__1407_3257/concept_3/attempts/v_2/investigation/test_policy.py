import sys, time, json, traceback
sys.path.insert(0, '/tmp/cascade-c3-g2-v2-0f0el7m5/participant/input')
from simulator import Device
import importlib, os
Policy = importlib.import_module(os.environ.get('POLICY_MODULE', 'policy')).Policy


def actual_kind(device, root):
    neighbors = device.neighbors[root]
    return 'R' if any(second in device.neighbors[first] and third in device.neighbors[first] and third in device.neighbors[second] for first in neighbors for second in neighbors for third in neighbors if first < second < third) else 'S'


cases = json.load(open('/tmp/cascade-c3-g2-v2-0f0el7m5/participant/input/dev_cases.json'))
if len(sys.argv) > 2:
    import random
    rng = random.Random(int(sys.argv[2]))
    cases = [dict(family=('RR','RS','SS')[index % 3], contamination_denominator=(8,6,4)[index // 3 % 3], seed=rng.getrandbits(128)) for index in range(int(sys.argv[1]))]
else:
    cases = cases[:int(sys.argv[1])] if len(sys.argv) > 1 else cases
correct = 0
for index, case in enumerate(cases):
    device = Device(case['family'], case['contamination_denominator'], case['seed'])
    policy = Policy(device.handle)
    started = time.process_time()
    try:
        family, posterior, budget = policy.run()
        correct += family == case['family']
        roots = [model.root for model in policy.models]
        kinds = [actual_kind(device, root) for root in roots]
        covered = len(set(roots + [target for root in roots for target in device.neighbors[root]]))
        print(index, case['family'], case['contamination_denominator'], family, [round(value,4) for value in posterior], budget, ''.join(kinds), covered, round(time.process_time()-started,3), 'OK' if family==case['family'] else 'WRONG', flush=True)
    except Exception:
        traceback.print_exc()
        break
print('TOTAL', correct, len(cases), flush=True)
