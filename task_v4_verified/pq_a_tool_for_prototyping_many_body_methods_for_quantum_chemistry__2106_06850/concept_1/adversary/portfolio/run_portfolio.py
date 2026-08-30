import argparse
import json
import math
import resource
import time
from collections import defaultdict
from pathlib import Path

from solve import search, validate


def geomean(values):
    return math.exp(sum(math.log(value) for value in values) / len(values))


def run(hidden, destination, seconds, trials, seed, delayed, exhaust_trials=False):
    started = time.monotonic()
    manifest = json.loads((hidden / 'manifest.json').read_text())
    destination.mkdir(parents=True, exist_ok=True)
    records = []
    families = defaultdict(list)
    for position, entry in enumerate(manifest['cases']):
        case = json.loads((hidden / entry['file']).read_text())
        plan, report = search(case, seconds, trials, seed + position * 101, delayed, exhaust_trials)
        result = validate(case, plan)
        name = Path(entry['file']).stem
        (destination / (name + '.plan.json')).write_text(json.dumps(plan))
        (destination / (name + '.search.json')).write_text(json.dumps(report, indent=2) + '\n')
        certificate = report['optimization'].get('root_certificate')
        if certificate:
            (destination / (name + '.bound.json')).write_text(json.dumps(certificate, indent=2) + '\n')
        record = {key: value for key, value in report.items() if key != 'candidates'}
        record['optimization'] = {key: value for key, value in report['optimization'].items() if key != 'root_certificate'}
        if certificate:
            record['optimization']['verified_integer_root_lower_flops'] = certificate['integer_lower_flops']
            record['optimization']['bound_certificate_file'] = name + '.bound.json'
        record.update({'file': entry['file'], 'family': entry['family'], 'baseline_flops': entry['baseline']['flops'],
                       'speedup': entry['baseline']['flops'] / result['flops'],
                       'relaxed_upper_speedup': entry['baseline']['flops'] / report['optimization']['joint_lower_flops']})
        records.append(record)
        families[entry['family']].append(record['speedup'])
        print(name, 'speedup', round(record['speedup'], 9), 'flops', result['flops'],
              'peak', result['peak_elements'], 'seconds', round(report['generation_seconds'], 3),
              'LP', report['optimization']['lp_nodes'], 'closed', report['optimization']['numerically_closed'],
              'valid_trials', report['validated_candidates'], 'invalid_trials', report['invalid_candidates'], flush=True)
        summary = {'classification': 'privileged offline optimization portfolio; not a participant attempt',
                   'targets': {'overall': manifest['target_geomean_speedup'], 'each_family': manifest['target_worst_family_speedup']},
                   'core_score': geomean([record['speedup'] for record in records]),
                   'family_scores': {family: geomean(values) for family, values in families.items()},
                   'all_valid': all(record['result']['valid'] for record in records),
                   'cases_completed': len(records), 'cases_expected': len(manifest['cases']),
                   'generation_seconds': sum(record['generation_seconds'] for record in records),
                   'elapsed_seconds': time.monotonic() - started,
                   'max_rss_kib': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
                   'cases': records}
        summary['worst_family_score'] = min(summary['family_scores'].values())
        summary['passed_fixed_arithmetic_targets'] = (len(records) == len(manifest['cases']) and summary['all_valid']
                                                      and summary['core_score'] >= manifest['target_geomean_speedup']
                                                      and summary['worst_family_score'] >= manifest['target_worst_family_speedup'])
        summary['conclusion'] = 'Passing privileged certificates found' if summary['passed_fixed_arithmetic_targets'] else 'No passing solution found; achievability unknown, not impossible'
        (destination / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n')
    return summary


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--seconds', type=float, default=20)
    parser.add_argument('--trials', type=int, default=32)
    parser.add_argument('--seed', type=int, default=0)
    parser.add_argument('--delayed', action='store_true')
    parser.add_argument('--exhaust-trials', action='store_true')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    run(root / 'evaluator/hidden', args.output, args.seconds, args.trials, args.seed, args.delayed, args.exhaust_trials)


if __name__ == '__main__':
    main()
