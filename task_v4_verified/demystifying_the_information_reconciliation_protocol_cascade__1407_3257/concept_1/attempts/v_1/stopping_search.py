import argparse
import json
import math
import time
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor, as_completed

from cascade_sim import choose_action, run_frame, validate_policy
from experiment import OUTPUT, load_suite, make_policy
from scoring import summarize


def stopped_policy(base, quiet, empty_quiet=12):
    policy = json.loads(json.dumps(base))
    policy['max_passes'] = 20
    policy['rules'] = [
        dict(when=[['pass_index', 'ge', 3], ['quiet_passes', 'ge', quiet], ['corrected_fraction', 'gt', 0]], action=dict(stop=True)),
        dict(when=[['pass_index', 'ge', 3], ['quiet_passes', 'ge', empty_quiet]], action=dict(stop=True)),
    ] + [rule for rule in base['rules'] if not rule['action'].get('stop')]
    return policy


def traced_worker(payload):
    name, base, variants, case, stress = payload
    records = defaultdict(list)
    base = json.loads(json.dumps(base))
    base['max_passes'] = 20
    base['rules'] = [rule for rule in base['rules'] if not rule['action'].get('stop')]
    entropy = -case['q_true']*math.log2(case['q_true'])-(1-case['q_true'])*math.log2(1-case['q_true'])
    for frame_index, seed in enumerate(case['frame_seeds']):
        full = run_frame(case, seed, base, errors=case['errors'][frame_index] if stress else None, trace=True)
        full_corrected = sum(step['corrected'] for step in full['trace'])
        for variant, policy in variants.items():
            disclosed, rounds, corrected, passes = 32, 1, 0, 0
            for step in full['trace']:
                if passes >= 3 and choose_action(policy, step['features'])['stop']:
                    break
                disclosed += step['disclosed']
                rounds += step['rounds']
                corrected += step['corrected']
                passes += 1
            failure = int(bool(full['failure']) or corrected < full_corrected)
            leakage = 1 if failure else min(1, disclosed/case['frame_bits'])
            records[variant].append(dict(seed=seed, failure=failure, disclosed=disclosed, rounds=rounds, passes=passes,
                                        effective_leakage=leakage, cost=leakage/entropy+case['latency']*rounds,
                                        peak_known=full['peak_known']))
    return name, 'stress' if stress else case['family'], dict(records)


def search(bases, suite, tag, quiet_values=(4,5,6,7,8,10,12), jobs=16, variant_builder=None):
    started = time.time()
    groups = defaultdict(lambda:defaultdict(list))
    candidates = {}
    payloads = []
    for name, base in bases.items():
        variants = ({f'{name}_quiet{quiet}':stopped_policy(base, quiet) for quiet in quiet_values}
                    if variant_builder is None else variant_builder(name,base))
        for policy in variants.values():
            validate_policy(policy)
        candidates.update(variants)
        payloads.extend((name, base, variants, case, False) for case in suite['cases'])
        payloads.extend((name, base, variants, case, True) for case in suite.get('stress', []))
    with ProcessPoolExecutor(max_workers=jobs) as executor:
        futures = [executor.submit(traced_worker, payload) for payload in payloads]
        for future in as_completed(futures):
            name, family, variants = future.result()
            for variant, records in variants.items():
                groups[variant][family].extend(records)
    reference = json.loads((OUTPUT / f"reference_{suite['split']}.json").read_text())
    references = defaultdict(list)
    for case in suite['cases']:
        references[case['family']].extend(reference[str(seed)] for seed in case['frame_seeds'])
    results = {}
    for name, families in groups.items():
        ratios = {family:summarize(records)['mean_cost']/summarize(references[family])['mean_cost']
                  for family,records in families.items() if family != 'stress'}
        results[name] = dict(ratio=sum(ratios.values())/len(ratios), ratios=ratios,
                            failures={family:sum(record['failure'] for record in records) for family,records in families.items()},
                            means={family:summarize(records) for family,records in families.items()})
    (OUTPUT / f'{tag}_results.json').write_text(json.dumps(results,indent=2))
    (OUTPUT / f'{tag}_policies.json').write_text(json.dumps(candidates,indent=2))
    (OUTPUT / f'{tag}_records.json').write_text(json.dumps(groups))
    for name, result in sorted(results.items(),key=lambda item:item[1]['ratio']):
        print(name,round(result['ratio'],4),{key:round(value,4) for key,value in sorted(result['ratios'].items())},result['failures'],flush=True)
    print('elapsed',round(time.time()-started,2),flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--split',default='dev')
    parser.add_argument('--tag',default='stopping_dev')
    parser.add_argument('--bases')
    arguments = parser.parse_args()
    bases = {}
    if arguments.bases:
        bases = json.loads((OUTPUT / arguments.bases).read_text())
    else:
        for first in [.75,1,1.25,1.5]:
            for basis, scale in [('remaining',1),('parity',3)]:
                for third in [.25,.5]:
                    name = f'first{first}_{basis}{scale}_third{third}'
                    bases[name] = make_policy(first=('estimate',first),second=(basis,scale),third=('frame',third))
    search(bases,load_suite(arguments.split),arguments.tag)
