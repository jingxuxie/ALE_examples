import argparse
import json
from pathlib import Path
import time

from solve import load_atlas, solve


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--seconds', type=float, default=12)
    parser.add_argument('--case', default='')
    args = parser.parse_args()
    input_root = Path(__file__).resolve().parents[2] / 'participant' / 'input'
    report = []
    for directory in sorted(input_root.iterdir()):
        if not directory.is_dir() or args.case not in directory.name:
            continue
        started = time.monotonic()
        choices = solve(directory, args.seconds)
        runtime = time.monotonic() - started
        atlas = load_atlas(directory)
        score = atlas.score(choices)
        gain = 1 - score['objective'] / atlas.metadata['baseline_objective']
        row = {'case': directory.name, 'gain': gain, 'runtime': runtime, **score}
        report.append(row)
        Path(directory.name + '_result.json').write_text(json.dumps({'choices': choices.tolist()}) + '\n')
        print(json.dumps(row), flush=True)
    Path('benchmark_results.json').write_text(json.dumps(report, indent=2) + '\n')
    print('mean gain', sum(row['gain'] for row in report) / len(report))


if __name__ == '__main__':
    main()
