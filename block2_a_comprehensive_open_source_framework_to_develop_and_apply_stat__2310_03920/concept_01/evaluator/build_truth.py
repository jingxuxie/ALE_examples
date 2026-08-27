import json
import os
from pathlib import Path
import subprocess
from metrics import read_output, error_metric

ROOT = Path(__file__).resolve().parents[1]


def run(case, profile, output, runner):
    output.mkdir(parents=True, exist_ok=True)
    with (output / 'run.log').open('w') as handle:
        subprocess.run(['bash', str(runner), str(case), str(output), profile], stdout=handle,
                       stderr=subprocess.STDOUT, check=True, timeout=600)
    return read_output(output)


def main():
    folder = ROOT / 'evaluator/hidden/truth'
    folder.mkdir(exist_ok=True)
    summaries = []
    for path in sorted((ROOT / 'evaluator/hidden/cases').glob('*.json')):
        case = json.loads(path.read_text())
        production_path = ROOT / 'solution/hidden_production' / case['id']
        if case['family'] == 'paired' or not (production_path / 'stats.json').exists():
            production = run(path, 'production', production_path, ROOT / 'solution/run.sh')
        else:
            production = read_output(production_path)
        refined = run(path, 'refined', ROOT / 'solution/hidden_refined' / case['id'], ROOT / 'solution/run.sh')
        weak = run(path, 'production', ROOT / 'solution/hidden_legacy' / case['id'], ROOT / 'solution/legacy_runner/run.sh')
        error, errors = error_metric(case, production, refined)
        weak_error, _ = error_metric(case, weak, refined)
        truth = {'case': case['id'], 'family': case['family'], 'rows': refined['rows'], 'initial_energy': refined['initial_energy'],
                 'strong_error': max(error, 1e-7), 'weak_error': weak_error, 'reference_errors': errors,
                 'reference_seconds': production['stats']['seconds'], 'reference_rss_mb': production['stats']['peak_rss_mb']}
        (folder / (case['id'] + '.json')).write_text(json.dumps(truth, indent=2))
        summary = {key: truth[key] for key in ['case', 'strong_error', 'weak_error', 'reference_seconds', 'reference_rss_mb']}
        summaries.append(summary)
        print(json.dumps(summary), flush=True)
    (folder / 'calibration.json').write_text(json.dumps(summaries, indent=2))


if __name__ == '__main__':
    main()
