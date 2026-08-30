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
from sandbox import run_submission
from metrics import case_metrics, summarize


def evaluate(submission, inputs_path, labels_path):
    started = time.monotonic()
    target = json.loads((ROOT / 'evaluator' / 'target.json').read_text())
    report = {'core_score': 0.0, 'worst_family_score': 0.0, 'runtime_resource_score': 0.0,
              'valid': False, 'passed': False}
    try:
        with tempfile.TemporaryDirectory(prefix='epw_spectral_') as temporary:
            output = Path(temporary)
            runtime = run_submission(submission, inputs_path, output, timeout=110, memory_mb=3072)
            report['runtime'] = runtime
            if runtime['returncode'] != 0 or runtime['timed_out']:
                raise ValueError('solver failed or exceeded runtime budget')
            result_path = output / 'result.npz'
            if not result_path.is_file() or result_path.is_symlink() or result_path.stat().st_size > 32 * 1024 ** 2:
                raise ValueError('missing, oversized, or nonregular output')
            with zipfile.ZipFile(result_path) as archive:
                if sum(member.file_size for member in archive.infolist()) > 64 * 1024 ** 2:
                    raise ValueError('expanded output exceeds size bound')
            with np.load(result_path, allow_pickle=False) as archive:
                if archive.files != ['alpha2f']:
                    raise ValueError('output must contain exactly alpha2f')
                prediction = archive['alpha2f']
            with np.load(inputs_path, allow_pickle=False) as archive:
                inputs = dict(archive)
            with np.load(labels_path, allow_pickle=False) as archive:
                truth = archive['alpha2f']
                family = archive['family']
            report.update(summarize(prediction, truth, family, inputs, target))
            losses, _ = case_metrics(prediction, truth, inputs)
            report['case_losses'] = losses.tolist()
            report['case_families'] = family.tolist()
        report['runtime_seconds'] = time.monotonic() - started
        report['runtime_resource_score'] = float(100 * max(0, 1 - report['runtime_seconds'] / 120))
        if report['runtime_seconds'] > 120:
            report.update(passed=False, reason='whole-evaluation runtime budget exceeded')
    except Exception as error:
        report.update(reason=f'{type(error).__name__}: {error}', runtime_seconds=time.monotonic() - started)
    return report


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--submission', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--validation', action='store_true')
    args = parser.parse_args()
    directory = ROOT / ('participant/input' if args.validation else 'evaluator/hidden')
    split = 'validation' if args.validation else 'test'
    report = evaluate(args.submission.resolve(), directory / f'{split}_input.npz', directory / f'{split}_labels.npz')
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, allow_nan=False) + '\n')
    print(json.dumps({key: value for key, value in report.items() if key not in ('runtime', 'case_losses', 'case_families')}, allow_nan=False))


if __name__ == '__main__':
    main()
