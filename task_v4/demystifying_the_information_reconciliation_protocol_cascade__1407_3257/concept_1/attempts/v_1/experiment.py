import argparse
import copy
import itertools
import json
import os
import time
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

from baseline import baseline_policy
from cascade_sim import run_frame, validate_policy
from scoring import evaluate_suite, summarize

ASSETS = Path('/tmp/cascade-c1-v1-pyern4cd/participant')
OUTPUT = Path(__file__).resolve().parent


def size(basis, scale):
    return dict(basis=basis, scale=scale, round='nearest')


def make_policy(first=('paper_first', 1), second=('paper_second', 1),
                third=('frame', .25), tail=.5, quiet=10, batch='smallest'):
    policy = baseline_policy()
    policy['max_passes'] = 20
    for action in policy['schedule']:
        action['batch'] = batch
    for index, formula in enumerate([first, second, third, ('frame', tail)]):
        policy['schedule'][index]['size'] = size(*formula)
    policy['rules'] = [dict(when=[['pass_index', 'ge', 3], ['quiet_passes', 'ge', quiet]], action=dict(stop=True))]
    validate_policy(policy)
    return policy


def load_suite(split, frames=None):
    path = ASSETS / 'input' / f'{split}.json' if split in {'train','dev'} else OUTPUT / f'{split}.json'
    suite = json.loads(path.read_text())
    if frames:
        for case in suite['cases'] + suite.get('stress', []):
            case['frame_seeds'] = case['frame_seeds'][:frames]
            if 'errors' in case:
                case['errors'] = case['errors'][:frames]
    return suite


def worker(payload):
    name, policy, case, stress = payload
    records = []
    for index, seed in enumerate(case['frame_seeds']):
        record = run_frame(case, seed, policy, errors=case['errors'][index] if stress else None)
        record['seed'] = seed
        records.append(record)
    return name, 'stress' if stress else case['family'], records


def run_candidates(candidates, suite, jobs=16, tag='search'):
    started = time.time()
    reference_path = OUTPUT / f"reference_{suite['split']}.json"
    reference = json.loads(reference_path.read_text()) if reference_path.exists() else {}
    payloads = []
    if not reference:
        payloads.extend(('reference', baseline_policy(), case, False) for case in suite['cases'])
    for name, policy in candidates.items():
        validate_policy(policy)
        payloads.extend((name, policy, case, False) for case in suite['cases'])
        payloads.extend((name, policy, case, True) for case in suite.get('stress', []))
    groups = defaultdict(lambda: defaultdict(list))
    with ProcessPoolExecutor(max_workers=jobs) as executor:
        futures = [executor.submit(worker, payload) for payload in payloads]
        for future in as_completed(futures):
            name, family, records = future.result()
            groups[name][family].extend(records)
    if 'reference' in groups:
        reference = {str(record['seed']): record for records in groups.pop('reference').values() for record in records}
        reference_path.write_text(json.dumps(reference))
    references = defaultdict(list)
    for case in suite['cases']:
        references[case['family']].extend(reference[str(seed)] for seed in case['frame_seeds'])
    results = {}
    for name, families in groups.items():
        ratios = {family: summarize(records)['mean_cost'] / summarize(references[family])['mean_cost']
                  for family, records in families.items() if family != 'stress'}
        results[name] = dict(ratio=sum(ratios.values()) / len(ratios), ratios=ratios,
                             failures={family:sum(record['failure'] for record in records) for family, records in families.items()},
                             means={family:summarize(records) for family, records in families.items()})
    (OUTPUT / f'{tag}_results.json').write_text(json.dumps(results, indent=2))
    (OUTPUT / f'{tag}_policies.json').write_text(json.dumps(candidates, indent=2))
    (OUTPUT / f'{tag}_records.json').write_text(json.dumps(groups))
    for name, result in sorted(results.items(), key=lambda item:item[1]['ratio']):
        print(name, round(result['ratio'], 4), {key:round(value,4) for key,value in sorted(result['ratios'].items())}, result['failures'], flush=True)
    print('elapsed', round(time.time()-started,2), flush=True)
    return results


def initial_grid():
    candidates = {'baseline': baseline_policy()}
    for first, second, batch in itertools.product(
            [('paper_first',1), ('paper_first',.5), ('estimate',.5), ('estimate',.75)],
            [('paper_second',1), ('paper_second',.5), ('first',2), ('first',4), ('parity',2), ('parity',4)],
            ['smallest']):
        name = f'{first[0]}{first[1]}_{second[0]}{second[1]}_{batch}'
        candidates[name] = make_policy(first=first, second=second)
    return candidates


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--split', default='train')
    parser.add_argument('--tag', default='initial')
    parser.add_argument('--candidates')
    parser.add_argument('--jobs', type=int, default=16)
    arguments = parser.parse_args()
    candidates = json.loads(Path(arguments.candidates).read_text()) if arguments.candidates else initial_grid()
    run_candidates(candidates, load_suite(arguments.split), arguments.jobs, arguments.tag)
