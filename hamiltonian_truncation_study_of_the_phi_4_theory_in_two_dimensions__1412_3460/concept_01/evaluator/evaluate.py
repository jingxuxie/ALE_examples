import argparse
import csv
import json
import math
import os
from pathlib import Path
import resource
import subprocess
import tempfile
import time

import numpy as np

ROOT = Path(__file__).resolve().parent.parent


def limits():
    resource.setrlimit(resource.RLIMIT_AS, (1536 * 1024**2, 1536 * 1024**2))
    resource.setrlimit(resource.RLIMIT_CPU, (300, 310))


def run_submission(submission, input_directory, destination):
    destination.mkdir(parents=True, exist_ok=True)
    command = ['/usr/bin/time', '-f', '%M', '-o', str(destination / 'launcher_maxrss.txt'),
               'bwrap', '--die-with-parent', '--unshare-net', '--unshare-pid',
               '--ro-bind', '/usr', '/usr', '--ro-bind', '/lib', '/lib',
               '--symlink', 'usr/bin', '/bin', '--symlink', 'usr/lib64', '/lib64',
               '--ro-bind', '/etc/alternatives', '/etc/alternatives',
               '--ro-bind', '/etc/ld.so.cache', '/etc/ld.so.cache',
               '--proc', '/proc', '--dev', '/dev', '--tmpfs', '/tmp',
               '--ro-bind', str(submission), '/submission',
               '--ro-bind', str(input_directory), '/input',
               '--bind', str(destination), '/output', '--chdir', '/output',
               '--setenv', 'HOME', '/tmp', '--setenv', 'PYTHONNOUSERSITE', '1',
               '--setenv', 'OPENBLAS_NUM_THREADS', '1', '--setenv', 'OMP_NUM_THREADS', '1',
               '--unsetenv', 'PYTHONPATH',
               '/usr/bin/time', '-f', '%M', '-o', '/output/maxrss.txt',
               '/bin/bash', '/submission/run.sh', '/input/campaign.json', '/output']
    started = time.perf_counter()
    try:
        completed = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                   text=True, timeout=305, preexec_fn=limits)
        output, code = completed.stdout, completed.returncode
    except subprocess.TimeoutExpired as error:
        output, code = str(error.stdout), 124
    (destination / 'execution.log').write_text(output)
    rss = 0.0
    if (destination / 'maxrss.txt').exists():
        for line in (destination / 'maxrss.txt').read_text().splitlines():
            try:
                rss = float(line) / 1024
            except ValueError:
                pass
    return {'returncode': code, 'seconds': time.perf_counter() - started, 'peak_rss_mb': rss}


def table(path):
    with Path(path).open() as handle:
        return list(csv.DictReader(handle))


def numeric(row, key):
    value = float(row[key])
    if not math.isfinite(value):
        raise ValueError('Nonfinite table entry')
    return value


def spectra_loss(rows, target, cutoff):
    selected = [row for row in rows if row['case'] == target['case']
                and abs(numeric(row, 'cutoff') - cutoff) < 1e-8 and row['method'] == 'production']
    energies = {(row['sector'], int(row['level'])): numeric(row, 'energy') for row in selected}
    if len(energies) != len(selected) or not energies:
        return 1e6, 'missing_or_duplicate_rows'
    vacuum = min(energies.values())
    values = []
    for key in target['keys']:
        if key == 'vacuum':
            values.append(vacuum)
        else:
            sector, level = key.rsplit(':', 1)
            if (sector, int(level)) not in energies:
                return 1e6, 'missing_levels'
            values.append(energies[(sector, int(level))] - vacuum)
    for row in selected:
        if abs(numeric(row, 'energy') - vacuum - numeric(row, 'gap')) > 2e-7:
            return 1e6, 'inconsistent_gap'
    difference = np.maximum(np.abs(np.asarray(values) - target['target']) - target['uncertainty'], 0)
    return float(np.mean(difference)), None


def evidence(submission, replay):
    checks, notes = {}, []
    try:
        submitted = table(submission / 'results.csv')
        regenerated = table(replay / 'results.csv')
        lookup = {(row['case'], row['method'], float(row['cutoff']), row['sector'], int(row['level'])): row
                  for row in regenerated}
        matches = sum(key in lookup and abs(numeric(row, 'energy') - numeric(lookup[key], 'energy')) < 2e-6
                      for row in submitted
                      for key in [(row['case'], row['method'], float(row['cutoff']), row['sector'], int(row['level']))])
        checks['table_replay'] = matches / max(len(submitted), len(regenerated), 1)
        combined = submitted + table(submission / 'ablation.csv')
        replay_combined = regenerated + table(replay / 'ablation.csv')
        replay_all = {(row['case'], row['method'], float(row['cutoff']), row['sector'], int(row['level'])): row
                      for row in replay_combined}
        combined_matches = 0
        for row in combined:
            key = (row['case'], row['method'], float(row['cutoff']), row['sector'], int(row['level']))
            if key in replay_all and abs(numeric(row, 'energy') - numeric(replay_all[key], 'energy')) < 2e-6:
                combined_matches += 1
        checks['table_replay'] = combined_matches / max(len(combined), len(replay_combined), 1)
        all_rows = {row['row_id']: row for row in combined}
        checks['unique_row_ids'] = float(len(all_rows) == len(combined))
        methods = set(row['method'] for row in combined if row['method'] != 'production')
        ablation_values = {}
        for row in combined:
            if row['method'] in methods:
                ablation_values.setdefault((row['case'], float(row['cutoff']), row['sector'], row['level']), {})[row['method']] = numeric(row, 'energy')
        distinct = len(methods) >= 2
        ordered_methods = sorted(methods)
        for first_index, first in enumerate(ordered_methods):
            for second in ordered_methods[first_index + 1:]:
                largest = max((abs(values[first] - values[second]) for values in ablation_values.values()
                               if first in values and second in values), default=0)
                distinct = distinct and largest > 1e-6
        checks['distinct_ablation'] = float(distinct)
        valid_claims = 0
        families = set()
        claims = json.loads((submission / 'claims.json').read_text())['claims']
        for claim in claims:
            try:
                selected = [all_rows[key] for key in claim['rows']]
                quantity = claim['quantity']
                consistent = len(selected) == 4 and len({(row['case'], row['sector'], row['level']) for row in selected}) == 1
                consistent = consistent and selected[0]['method'] == selected[1]['method'] == 'production'
                consistent = consistent and selected[2]['method'] == selected[3]['method'] != 'production'
                consistent = consistent and float(selected[0]['cutoff']) == float(selected[2]['cutoff'])
                consistent = consistent and float(selected[1]['cutoff']) == float(selected[3]['cutoff'])
                denominator = abs(numeric(selected[3], quantity) - numeric(selected[2], quantity))
                ratio = abs(numeric(selected[1], quantity) - numeric(selected[0], quantity)) / max(denominator, 1e-12)
                consistent = consistent and denominator > 1e-10 and abs(ratio - float(claim['value'])) < 1e-6 * max(1, ratio)
                consistent = consistent and claim['conclusion'] == ('improved' if ratio < 1 else 'not_improved')
                if consistent:
                    valid_claims += 1
                    families.add(selected[0]['family'])
            except (KeyError, ValueError, IndexError):
                pass
        checks['claims_supported'] = valid_claims / max(len(claims), 1) * min(1, len(families) / 5)
        sources = table(submission / 'figures' / 'source.csv')
        matched = 0
        for source in sources:
            row = all_rows.get(source['row_id'])
            if row and abs(numeric(source, 'x') - numeric(row, source['x_quantity'])) < 1e-6 and abs(numeric(source, 'y') - numeric(row, source['y_quantity'])) < 1e-6:
                matched += 1
        checks['figure_source_data'] = matched / max(len(sources), 1)
        checks['figures_present'] = float(all((submission / 'figures' / name).exists()
                                             for name in ['primary_result.png', 'robustness_or_scaling.png']))
        scaling = table(submission / 'scaling.csv')
        checks['scaling_valid'] = float(bool(scaling) and all(numeric(row, 'elapsed_s') > 0 and numeric(row, 'peak_rss_mb') > 0 and numeric(row, 'dimension') > 0 for row in scaling))
        checks['report_and_initial_baseline'] = float((submission / 'report.md').exists() and (submission / 'baseline').exists())
    except (OSError, KeyError, ValueError, TypeError) as error:
        notes.append(str(error))
    names = ['table_replay', 'unique_row_ids', 'distinct_ablation', 'claims_supported',
             'figure_source_data', 'figures_present', 'scaling_valid', 'report_and_initial_baseline']
    return {'score': sum(checks.get(name, 0) for name in names) / len(names), 'checks': checks, 'notes': notes}


def evaluate(submission, destination):
    destination.mkdir(parents=True, exist_ok=True)
    hidden_input = ROOT / 'evaluator' / 'hidden' / 'input'
    public_input = ROOT / 'participant' / 'v_01' / 'input'
    resources = run_submission(submission, hidden_input, destination / 'hidden_replay')
    public_resources = run_submission(submission, public_input, destination / 'public_replay')
    targets = json.loads((ROOT / 'evaluator' / 'hidden' / 'targets.json').read_text())
    try:
        rows = table(destination / 'hidden_replay' / 'results.csv')
    except OSError:
        rows = []
    families, details = {}, []
    for target in targets:
        scores = []
        for cutoff_string, baseline in target['baselines'].items():
            cutoff = float(cutoff_string)
            try:
                loss, error = spectra_loss(rows, target, cutoff)
            except (ValueError, KeyError, TypeError) as failure:
                loss, error = 1e6, str(failure)
            scale = max(baseline['raw_loss'] - baseline['reference_loss'], 1e-8)
            score = float(np.clip(0.97 * (baseline['raw_loss'] - loss) / scale, 0, 1))
            scores.append(score)
            details.append({'case': target['case'], 'family': target['family'], 'cutoff': cutoff,
                            'loss': loss, 'score': score, 'error': error, **baseline})
        families[target['family']] = float(np.mean(scores))
    core = 0.65 * float(np.mean(list(families.values()))) + 0.35 * min(families.values())
    evidence_result = evidence(submission, destination / 'public_replay')
    resource_score = 0.5 / (1 + resources['seconds'] / 120) + 0.5 / (1 + resources['peak_rss_mb'] / 600)
    overall = 0.85 * core + 0.10 * evidence_result['score'] + 0.05 * resource_score
    classification = 'too_easy' if core >= 0.9 else 'moderate' if core >= 0.6 else 'potentially_hard'
    if resources['returncode'] != 0:
        classification = 'execution_failure_requires_review'
    result = {'overall_score': overall, 'core_score': core, 'per_family': families,
              'resource_score': resource_score, 'hidden_resources': resources,
              'public_resources': public_resources, 'evidence': evidence_result,
              'classification': classification, 'details': details}
    (destination / 'evaluation.json').write_text(json.dumps(result, indent=2))
    print(json.dumps({key: value for key, value in result.items() if key != 'details'}, indent=2))
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('submission')
    parser.add_argument('destination')
    arguments = parser.parse_args()
    evaluate(Path(arguments.submission).resolve(), Path(arguments.destination).resolve())
