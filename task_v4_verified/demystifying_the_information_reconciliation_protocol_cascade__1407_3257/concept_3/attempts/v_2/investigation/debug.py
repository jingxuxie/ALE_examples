import sys, random
sys.path.insert(0, '/tmp/cascade-c3-g2-v2-0f0el7m5/participant/input')
from simulator import Device
from policy_v5 import Policy

rng = random.Random(994185)
cases = [dict(family=('RR','RS','SS')[index % 3], contamination_denominator=(8,6,4)[index // 3 % 3], seed=rng.getrandbits(128)) for index in range(90)]
failures = [int(line.split()[0]) for line in open('fresh_v5.txt') if line.rstrip().endswith('WRONG')]
for index in failures[:8]:
    case = cases[index]
    device = Device(case['family'], case['contamination_denominator'], case['seed'])
    policy = Policy(device.handle)
    result = policy.run()
    print('CASE', index, case['family'],case['contamination_denominator'], result, flush=True)
    for model in policy.models:
        neighbors = device.neighbors[model.root]
        kind = 'R' if any(second in device.neighbors[first] and third in device.neighbors[first] and third in device.neighbors[second] for first in neighbors for second in neighbors for third in neighbors if first < second < third) else 'S'
        membership = model.membership()
        print('ROOT', model.root, kind, 'prob',model.probability(),'q',model.contamination,'counts_true',sorted(policy.counts[model.root][site] for site in neighbors),'counts_false', sorted((count for site,count in enumerate(policy.counts[model.root]) if site not in neighbors), reverse=True)[:7], 'sources_true', [site in neighbors for site in model.sources], 'members',[(site,round(membership[site],3),site in neighbors) for site in sorted(range(32),key=membership.__getitem__,reverse=True)[:8]],flush=True)
