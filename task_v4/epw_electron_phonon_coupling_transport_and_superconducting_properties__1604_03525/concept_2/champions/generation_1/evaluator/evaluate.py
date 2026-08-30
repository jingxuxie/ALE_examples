import argparse
import json
from pathlib import Path
import sys
import tempfile
import time
import zipfile
import numpy as np


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT.parent / 'authoring'))
sys.path.insert(0, str(ROOT / 'participant' / 'workspace'))
from sandbox import run_submission
from physics import score


def evaluate(submission, hidden):
    manifest = json.loads((hidden / 'manifest.json').read_text())
    rows = []
    started = time.monotonic()
    for item in manifest:
        row = dict(name=item['name'], family=item['family'], score=0.0, valid=False)
        try:
            with tempfile.TemporaryDirectory(prefix='epw_coreset_') as temporary:
                output = Path(temporary)
                runtime = run_submission(submission, hidden / item['path'], output, timeout=90)
                row['runtime'] = runtime
                if runtime['returncode'] != 0 or runtime.get('timed_out', False):
                    raise ValueError('submission process failed or exceeded its runtime limit')
                result_path = output / 'result.npz'
                if not result_path.is_file() or result_path.is_symlink() or result_path.stat().st_size > 32 * 1024 ** 2:
                    raise ValueError('missing, oversized, or symlinked output')
                with zipfile.ZipFile(result_path) as archive:
                    if sum(member.file_size for member in archive.infolist()) > 64 * 1024 ** 2:
                        raise ValueError('expanded output exceeds the array-size limit')
                with np.load(result_path, allow_pickle=False) as result:
                    indices = result['indices']
                    multipliers = result['multipliers']
                with np.load(hidden / item['path'], allow_pickle=False) as catalogue:
                    row.update(score(catalogue, indices, multipliers))
                row.update(valid=True, reason='physical diagnostics evaluated')
        except Exception as error:
            row['reason'] = f'{type(error).__name__}: {error}'
        rows.append(row)
    families = sorted(set(row['family'] for row in rows))
    family_scores = {family: float(np.mean([row['score'] for row in rows if row['family'] == family]))
                     for family in families}
    core_score = float(np.mean([row['score'] for row in rows]))
    worst_family_score = min(family_scores.values())
    valid = all(row['valid'] for row in rows)
    passed = valid and core_score >= 80 and worst_family_score >= 70
    runtime_seconds = time.monotonic() - started
    return {'core_score': core_score, 'worst_family_score': worst_family_score,
            'family_scores': family_scores, 'runtime_seconds': runtime_seconds,
            'runtime_resource_score': float(100 * max(0, 1 - runtime_seconds / (90 * len(rows)))),
            'baseline_core_score': 0.17132318233178215, 'valid': valid, 'passed': passed,
            'reason': 'fixed improvement target met' if passed else
                      ('invalid submission or resource failure' if not valid else 'below fixed quality or worst-family target'),
            'cases': rows}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--submission', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--hidden', type=Path, default=ROOT / 'evaluator' / 'hidden')
    args = parser.parse_args()
    report = evaluate(args.submission.resolve(), args.hidden.resolve())
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, allow_nan=False) + '\n')
    print(json.dumps({key: value for key, value in report.items() if key != 'cases'}, allow_nan=False))


if __name__ == '__main__':
    main()
