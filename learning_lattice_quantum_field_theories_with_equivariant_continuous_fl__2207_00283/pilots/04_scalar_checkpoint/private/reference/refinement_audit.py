import json
import argparse
from pathlib import Path
import numpy as np
from author import ROOT, evaluate


def errors(actual, target, initial):
    result = {}
    for name in target:
        reference = target[name] - (initial['logp'] if name == 'logp' else 0.)
        difference = actual[name] - target[name]
        floor = 1.0 if name == 'logp' else 1e-3
        rms = float(np.sqrt(np.mean(difference**2))) / max(float(np.sqrt(np.mean(reference**2))), floor)
        maximum = float(np.max(np.abs(difference))) / max(float(np.max(np.abs(reference))), floor)
        relative = (rms + maximum) / 2
        result[name] = {'relative_error': relative, 'accuracy_score': 1 / (1 + relative / 2e-4)}
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--all', action='store_true')
    parser.add_argument('--cases', nargs='+')
    parser.add_argument('--report', type=Path, default=ROOT / 'private/reference/refinement_audit.json')
    args = parser.parse_args()
    report_path = args.report
    records = []
    for pool, folder in (('test', ROOT / 'private/reference/cases'), ('challenge', ROOT / 'private/challenge_pool')):
        manifest = json.loads((folder / 'manifest.json').read_text())
        for record in manifest['cases']:
            if record['operation'] == 'probe':
                continue
            if args.cases and record['id'] not in args.cases:
                continue
            if not args.all and record['id'] not in ('forward32', 'forward64', 'conditional_reverse64'):
                continue
            data = dict(np.load(folder / record['input'], allow_pickle=False))
            coarse = dict(np.load(folder / record['expected'], allow_pickle=False))
            medium, medium_time = evaluate(data, steps=200)
            fine, fine_time = evaluate(data, steps=400)
            output_dir = ROOT / 'private/reference/refined' / pool
            output_dir.mkdir(parents=True, exist_ok=True)
            np.savez(output_dir / (record['id'] + '.200.npz'), **medium)
            np.savez(output_dir / (record['id'] + '.400.npz'), **fine)
            item = {'id': record['id'], 'pool': pool,
                    '100_vs_200': errors(coarse, medium, data),
                    '100_vs_400': errors(coarse, fine, data),
                    '200_vs_400': errors(medium, fine, data),
                    'medium_timing': medium_time, 'fine_timing': fine_time}
            records.append(item)
            report_path.write_text(json.dumps(records, indent=2))
            print(json.dumps(item), flush=True)


if __name__ == '__main__':
    main()
