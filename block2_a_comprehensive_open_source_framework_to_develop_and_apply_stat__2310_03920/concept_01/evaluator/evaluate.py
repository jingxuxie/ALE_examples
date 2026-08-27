import argparse
import json
import math
from pathlib import Path
import time
import numpy as np
from evidence import verify
from metrics import read_output, error_metric, quality
from sandbox_run import execute

ROOT = Path(__file__).resolve().parents[1]


def evaluate(submission, output, evidence=True):
    started = time.perf_counter()
    submission, output = Path(submission).resolve(), Path(output).resolve()
    output.mkdir(parents=True, exist_ok=True)
    assets = ROOT / 'participant/v_01'
    families = {}
    for case_path in sorted((ROOT / 'evaluator/hidden/cases').glob('*.json')):
        case = json.loads(case_path.read_text())
        truth = json.loads((ROOT / 'evaluator/hidden/truth' / case_path.name).read_text())
        run = output / 'hidden_runs' / case['id']
        execution = execute(submission, assets, case_path, run)
        record = {'core_score': 0.0, 'efficiency': 0.0, **execution}
        if execution['status'] == 'ok':
            try:
                measured = read_output(run)
                error, errors = error_metric(case, measured, truth)
                score = quality(error, truth['weak_error'], truth['strong_error'])
                time_ratio = execution['seconds'] / max(truth['reference_seconds'], 1)
                memory_ratio = execution['peak_rss_mb'] / max(truth['reference_rss_mb'] + 40, 160)
                efficiency = math.exp(-0.15 * max(0, math.log2(time_ratio)) - 0.08 * max(0, math.log2(memory_ratio)))
                record.update(core_score=score, normalized_error=error, errors=errors, efficiency=efficiency)
            except Exception as error:
                record.update(status='invalid_output', error=type(error).__name__ + ': ' + str(error))
        families[case['family']] = record
        print(json.dumps({'family': case['family'], **record}), flush=True)
    scores = [record['core_score'] for record in families.values()]
    core = 0.65 * float(np.mean(scores)) + 0.35 * min(scores)
    efficiency = float(np.mean([record['efficiency'] for record in families.values()]))
    evidence_result = verify(submission, assets, output / 'evidence_reruns') if evidence else {'score': 0, 'skipped': True}
    overall = core * (0.85 + 0.1 * efficiency + 0.05 * evidence_result['score'])
    result = {'core_score': core, 'overall_score': overall, 'minimum_family_score': min(scores),
              'per_family': families, 'efficiency': efficiency, 'evidence': evidence_result,
              'evaluation_seconds': time.perf_counter() - started,
              'classification': 'too_easy' if core >= 0.90 else 'moderate' if core >= 0.60 else 'potentially_hard'}
    (output / 'evaluation.json').write_text(json.dumps(result, indent=2))
    print(json.dumps(result, indent=2), flush=True)
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--submission', required=True)
    parser.add_argument('--output', required=True)
    parser.add_argument('--skip-evidence', action='store_true')
    arguments = parser.parse_args()
    evaluate(arguments.submission, arguments.output, not arguments.skip_evidence)
