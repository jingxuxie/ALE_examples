import argparse
import csv
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import time

import numpy as np

from qualification.model import load_case, summarize, triangle_geometry


CONCEPT = Path(__file__).resolve().parents[1]
PARTICIPANT = (CONCEPT / 'participant/v_01').resolve()
RUNTIME = PARTICIPANT / 'workspace/runtime'
PUBLIC_INPUT = CONCEPT / 'evaluator/public_input'
KEYS = ['stream', 'current', 'field', 'hole_current', 'fluxoid', 'inductance']
WEIGHTS = dict(stream=0.19, current=0.16, field=0.28, hole_current=0.10, fluxoid=0.10, inductance=0.17)


def execute(submission, case_path, save_dir, config=None):
    save_dir.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='thinfilm-eval-') as temporary:
        staging = Path(temporary)
        writable_submission = staging / 'submission'
        shutil.copytree(submission, writable_submission, symlinks=True)
        shutil.copy2(case_path, staging / 'case.npz')
        shutil.copy2(case_path.with_suffix('.json'), staging / 'case.json')
        command = ['bwrap', '--die-with-parent', '--unshare-net', '--unshare-pid',
                   '--ro-bind', '/usr', '/usr', '--ro-bind', '/bin', '/bin',
                   '--ro-bind', '/lib', '/lib', '--ro-bind', '/lib64', '/lib64',
                   '--proc', '/proc', '--dev', '/dev', '--tmpfs', '/tmp',
                   '--ro-bind', str(PARTICIPANT), str(PARTICIPANT),
                   '--bind', str(writable_submission), str(submission),
                   '--bind', str(staging), '/work', '--chdir', str(submission)]
        for system_file in ['/etc/ld.so.cache', '/etc/fonts']:
            if Path(system_file).exists():
                command += ['--ro-bind', system_file, system_file]
        command += ['/usr/bin/time', '-f', '%e %M', '-o', '/work/time.txt',
                    '/bin/bash', str(submission / 'run.sh'), 'case', '/work/case.npz', '/work/result.npz']
        if config is not None:
            command += ['--config', config]
        environment = {'PATH': '/usr/bin:/bin', 'HOME': '/tmp', 'LANG': 'C.UTF-8',
                       'ALE_RUNTIME': str(RUNTIME), 'PYTHONPATH': str(RUNTIME),
                       'PYTHONNOUSERSITE': '1', 'OPENBLAS_NUM_THREADS': '1', 'OMP_NUM_THREADS': '1',
                       'NUMBA_NUM_THREADS': '1', 'MPLBACKEND': 'Agg'}
        start = time.perf_counter()
        try:
            process = subprocess.run(command, env=environment, capture_output=True, text=True, timeout=60)
            error = None if process.returncode == 0 else f'exit_{process.returncode}'
            transcript = process.stdout + '\n' + process.stderr
        except subprocess.TimeoutExpired as exception:
            error = 'case_timeout'
            transcript = str(exception)
        elapsed = time.perf_counter() - start
        (save_dir / 'process.log').write_text(transcript)
        metadata = {'seconds': elapsed, 'max_rss_mib': 0, 'error': error}
        if (staging / 'time.txt').exists():
            values = (staging / 'time.txt').read_text().strip().splitlines()[-1].split()
            if len(values) == 2:
                metadata['process_seconds'] = float(values[0])
                metadata['max_rss_mib'] = float(values[1]) / 1024
        if metadata['max_rss_mib'] > 4096:
            metadata['error'] = 'resident_memory_limit'
        result = None
        if (staging / 'result.npz').exists():
            shutil.copy2(staging / 'result.npz', save_dir / 'result.npz')
            try:
                with np.load(staging / 'result.npz', allow_pickle=False) as archive:
                    result = {key: archive[key] for key in KEYS}
            except Exception as exception:
                metadata['error'] = f'invalid_output: {exception}'
        else:
            metadata['error'] = metadata['error'] or 'missing_output'
        (save_dir / 'resources.json').write_text(json.dumps(metadata, indent=2))
        return result, metadata


def relative_error(value, expected, local=False):
    if value.shape != expected.shape or not np.all(np.isfinite(value)):
        return 1e6
    if not expected.size:
        return 0.0
    denominator = max(float(np.linalg.norm(expected)), 1e-10)
    global_error = float(np.linalg.norm(value - expected)) / denominator
    if local:
        magnitude = np.linalg.norm(expected, axis=-1)
        delta = np.linalg.norm(value - expected, axis=-1)
        floor = max(0.15 * np.sqrt(np.mean(magnitude ** 2)), 1e-10)
        tail = float(np.quantile(delta / np.maximum(magnitude, floor), 0.95))
        return 0.7 * global_error + 0.3 * tail
    return global_error


def quality(error):
    return float(1 / (1 + (max(error, 0) / 0.08) ** 1.3))


def score_case(case, result, oracle):
    errors, scores = {}, {}
    for key in KEYS:
        errors[key] = relative_error(result[key], oracle[key], local=key in ['field', 'current'])
        scores[key] = quality(errors[key])
    _, _, current_x, current_y = triangle_geometry(case)
    if result['stream'].shape == oracle['stream'].shape:
        derived = np.stack(((current_x @ result['stream'].T).T, (current_y @ result['stream'].T).T), axis=-1)
        errors['current_consistency'] = relative_error(result['current'], derived)
        reactions = result['stream'] @ oracle['reaction'].T + oracle['reaction_offset']
        errors['fluxoid_consistency'] = relative_error(result['fluxoid'], reactions)
        boundary = float(np.max(np.abs(result['stream'][:, case.region == -1]), initial=0))
        hole_errors = []
        for hole in range(case.prescribed_current.shape[1]):
            values = result['stream'][:, case.region == hole + 1]
            hole_errors.append(float(np.max(np.abs(values - result['hole_current'][:, hole, None]))))
        errors['topology_consistency'] = max([boundary, *hole_errors]) / max(float(np.max(np.abs(oracle['stream']))), 1e-9)
        consistency = np.mean([quality(errors[key]) for key in ['current_consistency', 'fluxoid_consistency', 'topology_consistency']])
    else:
        consistency = 0.0
    weights = {key: value for key, value in WEIGHTS.items() if oracle[key].size}
    accuracy = sum(weights[key] * scores[key] for key in weights) / sum(weights.values())
    return float(accuracy * (0.8 + 0.2 * consistency)), errors, scores


def table_rows(path):
    return list(csv.DictReader(path.open()))


def selector(row, selection):
    return all(str(row.get(key)) == str(value) for key, value in selection.items())


def evidence(submission, save_dir):
    checks, messages = [], []
    paths = ['results.csv', 'ablation.csv', 'scaling.csv', 'claims.json', 'report.md',
             'figures/primary_result.png', 'figures/robustness_or_scaling.png']
    checks.append(all((submission / path).is_file() for path in paths))
    try:
        results = table_rows(submission / 'results.csv')
        ablations = table_rows(submission / 'ablation.csv')
        scaling = table_rows(submission / 'scaling.csv')
        configs = sorted({row['configuration'] for row in ablations})
        defaults = {row['configuration'] for row in results}
        checks.append(len(configs) >= 2 and len(defaults) == 1)
        all_match = True
        raw_results = {}
        for filename in json.loads((PUBLIC_INPUT / 'suite.json').read_text())['cases']:
            case = load_case(PUBLIC_INPUT / filename)
            for config in configs:
                with np.load(submission / 'raw' / config / filename) as archive:
                    raw = {key: archive[key] for key in KEYS}
                raw_results[(case.meta['id'], config)] = raw
                for measured in summarize(case, raw):
                    matches = [row for row in ablations if selector(row, {'case': case.meta['id'], 'configuration': config, 'drive': measured['drive']})]
                    if len(matches) != 1:
                        all_match = False
                        continue
                    for key, value in measured.items():
                        if isinstance(value, (float, int)):
                            all_match &= bool(np.isclose(float(matches[0][key]), value, rtol=1e-5, atol=1e-8))
                    if config in defaults:
                        matches_result = [row for row in results if selector(row, {'case': case.meta['id'], 'configuration': config, 'drive': measured['drive']})]
                        all_match &= len(matches_result) == 1 and all(matches_result[0].get(key) == matches[0].get(key) for key in measured)
        checks.append(bool(all_match))
        rerun_matches = True
        for config in configs[:4]:
            raw, resource = execute(submission, PUBLIC_INPUT / 'dev_stack.npz', save_dir / config, config)
            expected = raw_results[('dev_stack', config)]
            rerun_matches &= raw is not None and resource['error'] is None and all(relative_error(raw[key], expected[key]) < 1e-5 for key in KEYS)
        checks.append(bool(rerun_matches))
        distinct = any(relative_error(raw_results[(case, configs[0])]['field'], raw_results[(case, other)]['field']) > 1e-5
                       for case in {row['case'] for row in ablations} for other in configs[1:])
        checks.append(bool(distinct))
        claims = json.loads((submission / 'claims.json').read_text())['claims']
        supported = len(claims) >= 2
        for claim in claims:
            rows = results if claim['table'] == 'results.csv' else ablations
            left = [row for row in rows if selector(row, claim['left'])]
            right = [row for row in rows if selector(row, claim['right'])]
            if len(left) != 1 or len(right) != 1:
                supported = False
                continue
            first, second = float(left[0][claim['metric']]), float(right[0][claim['metric']])
            relations = {'lt': first < second, 'gt': first > second,
                         'close': abs(first - second) <= float(claim.get('tolerance', 1e-8))}
            supported &= relations.get(claim['relation'], False) and bool(claim['text'])
        checks.append(bool(supported))
        measured_resources = all(float(row['seconds']) > 0 and float(row['max_rss_mib']) > 0 and int(row['vertices']) > 0 for row in scaling)
        checks.append(bool(measured_resources and len(scaling) >= len(configs) * 4))
        checks.append(len((submission / 'report.md').read_text().split()) >= 120)
    except Exception as exception:
        messages.append(str(exception))
        checks.extend([False] * max(0, 8 - len(checks)))
    return {'score': float(np.mean(checks)), 'checks': checks, 'messages': messages}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--submission', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--skip-evidence', action='store_true')
    args = parser.parse_args()
    submission = args.submission.resolve()
    save_dir = args.output.resolve().with_suffix('')
    save_dir.mkdir(parents=True, exist_ok=True)
    manifest = json.loads((CONCEPT / 'evaluator/oracles/manifest.json').read_text())
    families, resource_scores = {}, []
    for identifier, specification in manifest.items():
        path = CONCEPT / 'evaluator/hidden' / f'{identifier}.npz'
        case = load_case(path)
        result, resources = execute(submission, path, save_dir / identifier)
        score, errors, components = 0., {}, {}
        if result is not None and resources['error'] is None:
            try:
                with np.load(CONCEPT / 'evaluator/oracles' / path.name) as archive:
                    oracle = dict(archive)
                score, errors, components = score_case(case, result, oracle)
            except Exception as exception:
                resources['error'] = f'output_contract: {exception}'
        resource_score = 1 / (1 + 0.04 * max(0, resources['seconds'] / max(2, specification['reference_seconds']) - 1))
        resource_score *= 1 / (1 + max(0, resources['max_rss_mib'] / 450 - 1))
        resource_scores.append(resource_score if resources['error'] is None else 0)
        families[specification['family']] = {'score': score, 'errors': errors, 'components': components, 'resources': resources}
        print(specification['family'], round(score, 6), resources, flush=True)
    family_scores = [value['score'] for value in families.values()]
    core = 0.7 * np.mean(family_scores) + 0.3 * min(family_scores)
    evidence_result = {'score': 0, 'skipped': True} if args.skip_evidence else evidence(submission, save_dir / 'evidence')
    resource_score = float(np.mean(resource_scores))
    overall = 0.85 * core + 0.10 * resource_score + 0.05 * evidence_result['score']
    classification = 'too_easy' if core >= 0.90 else 'moderate' if core >= 0.60 else 'potentially_hard'
    infrastructure = any('bwrap:' in (save_dir / identifier / 'process.log').read_text() for identifier in manifest)
    if infrastructure:
        classification = 'invalid_infrastructure'
    output = {'core_score': float(core), 'overall_score': float(overall), 'mean_family_score': float(np.mean(family_scores)),
              'worst_family_score': float(min(family_scores)), 'per_family': families,
              'resource_score': resource_score, 'evidence': evidence_result, 'classification': classification,
              'evaluator_version': 'v_01_frozen', 'infrastructure_failure': infrastructure}
    args.output.write_text(json.dumps(output, indent=2))
    print(json.dumps({key: value for key, value in output.items() if key not in ['per_family', 'evidence']}, indent=2))


if __name__ == '__main__':
    main()
