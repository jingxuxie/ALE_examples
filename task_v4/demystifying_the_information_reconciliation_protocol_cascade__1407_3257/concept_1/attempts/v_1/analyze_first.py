import json
import random
from collections import defaultdict
from cascade_sim import stable_seed
from experiment import load_suite


def estimate(case, seed):
    source = random.Random(stable_seed(seed,'estimate'))
    probability = min(.15,max(.0001,case['q_true']*case['estimate_bias']))
    count = sum(source.random()<probability for unused in range(case['sample_size']))
    return min(.15,max(1/case['frame_bits'],(count+.5)/(case['sample_size']+1)))


if __name__ == '__main__':
    records = json.load(open('stopping_dev_records.json'))
    data = {}
    for case in load_suite('dev')['cases']:
        for seed in case['frame_seeds']:
            data[seed] = dict(case,estimate=estimate(case,seed))
    selected = [f'first{first}_parity3_third0.5_quiet7' for first in [.75,1,1.25,1.5]]
    print('Bandwidth cost by estimated QBER:')
    for lower,upper in [(0,.004),(.004,.008),(.008,.016),(.016,.032),(.032,.064),(.064,1)]:
        for name in selected:
            group = [record for record in records[name]['bandwidth'] if lower<=data[record['seed']]['estimate']<upper]
            print(lower,upper,name,'count',len(group),'cost',round(sum(record['cost'] for record in group)/max(1,len(group)),4),'fail',sum(record['failure'] for record in group))
