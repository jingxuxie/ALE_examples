import argparse
import copy
import json
from experiment import OUTPUT, load_suite
from stopping_search import search


def phase_policy(base,fast=4,last_pass=2,slow=9,low_count=10):
    policy=copy.deepcopy(base)
    rules=[]
    for frame_bits in [512,1024,2048,4096,8192]:
        rules.append(dict(when=[['pass_index','ge',3],['frame_bits','ge',frame_bits],['frame_bits','le',frame_bits],
                               ['corrected_fraction','le',2/frame_bits],['quiet_passes','lt',low_count]],action=dict(stop=False)))
    rules.extend([
        dict(when=[['pass_index','ge',fast+last_pass+1],['quiet_passes','ge',fast],['quiet_passes','lt',fast+1],['corrected_fraction','gt',0]],action=dict(stop=True)),
        dict(when=[['pass_index','ge',3],['quiet_passes','ge',slow],['corrected_fraction','gt',0]],action=dict(stop=True)),
        dict(when=[['pass_index','ge',3],['quiet_passes','ge',14]],action=dict(stop=True)),
    ])
    rules.extend(rule for rule in base['rules'] if 'stop' not in rule['action'])
    policy['rules']=rules
    return policy


def variants(name,base):
    return {f'{name}_fast{fast}_last{last}_slow{slow}':phase_policy(base,fast,last,slow)
            for fast in [3,4,5,6] for last in [2,3,4] for slow in [8,9,10]}


if __name__ == '__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--split',default='dev')
    parser.add_argument('--frames',type=int)
    arguments=parser.parse_args()
    bases={
        'learned':json.loads((OUTPUT/'stage2_candidates.json').read_text())['stage2_depth2_min100'],
        'plain':json.loads((OUTPUT/'inverse_dev_policies.json').read_text())['mixed0_third0.25_fast5_slow9_factor1.5'],
    }
    for base in bases.values():
        base['rules']=[rule for rule in base['rules'] if 'stop' not in rule['action']]
    search(bases,load_suite(arguments.split,arguments.frames),f'phase_{arguments.split}',variant_builder=variants)
