import argparse
import hashlib
import json
import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'participant' / 'workspace'))
sys.path.insert(0, str(ROOT / 'evaluator'))
from atlas import Atlas
from isolation import replay, safe_tree


def fingerprints(directory):
    return {str(path.relative_to(directory)): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in sorted(Path(directory).rglob('*')) if path.is_file()}


def verify_frozen_package():
    manifest_path = ROOT / 'frozen_manifest.json'
    if not manifest_path.exists():
        return None
    manifest = json.loads(manifest_path.read_text())
    for filename, expected in manifest['sha256'].items():
        if hashlib.sha256((ROOT / filename).read_bytes()).hexdigest() != expected:
            raise ValueError(f'frozen package changed: {filename}')
    return hashlib.sha256(manifest_path.read_bytes()).hexdigest()


def validate_result(result, atlas):
    if not isinstance(result, dict) or set(result) != {'choices'}:
        raise ValueError('output must contain exactly choices')
    choices = result['choices']
    if not isinstance(choices, list) or len(choices) != atlas.vertices:
        raise ValueError('wrong number of choices')
    if any(type(choice) is not int or not 0 <= choice < atlas.candidates for choice in choices):
        raise ValueError('choices must be in-range JSON integers, not bools')
    return atlas.score(choices)


def aggregate(rows, policy):
    family_names = sorted({row['family'] for row in rows})
    families = {}
    for family in family_names:
        members = [row for row in rows if row['family'] == family]
        gains = [row.get('gain', -1.0) for row in members]
        families[family] = {'mean_gain': sum(gains) / len(gains), 'minimum_case_gain': min(gains),
                            'all_feasible': all(row.get('feasible', False) for row in members),
                            'cases': len(members)}
    mean_gain = sum(row['mean_gain'] for row in families.values()) / len(families)
    worst_family_gain = min(row['mean_gain'] for row in families.values())
    minimum_case_gain = min(row.get('gain', -1.0) for row in rows)
    valid = all(row.get('feasible', False) and not row.get('runtime', {}).get('error') for row in rows)
    passed = valid and mean_gain >= policy['mean_gain_min'] and worst_family_gain >= policy['worst_family_gain_min'] and minimum_case_gain >= policy['minimum_case_gain']
    runtime_seconds = sum(row.get('runtime', {}).get('wall_seconds', 0.0) for row in rows)
    resource_compliant = [row.get('runtime', {}).get('returncode') == 0
                          and not row.get('runtime', {}).get('timed_out', False)
                          and row.get('runtime', {}).get('wall_seconds', float('inf')) <= row.get('runtime', {}).get('wall_limit_seconds', 0)
                          for row in rows]
    resource_score = sum(resource_compliant) / len(rows)
    failures = []
    if not valid:
        failures.append('one or more cases failed execution, output validation, or feasibility')
    if mean_gain < policy['mean_gain_min']:
        failures.append('family-balanced gain below fixed target')
    if worst_family_gain < policy['worst_family_gain_min']:
        failures.append('worst-family gain below fixed target')
    if minimum_case_gain < policy['minimum_case_gain']:
        failures.append('at least one case worse than baseline')
    return {'valid': valid, 'passed': bool(passed), 'family_balanced_gain': mean_gain,
            'worst_family_gain': worst_family_gain, 'minimum_case_gain': minimum_case_gain, 'families': families,
            'core_score': mean_gain, 'worst_family_score': worst_family_gain,
            'runtime_seconds': runtime_seconds, 'resource_score': resource_score,
            'runtime_resource_score': resource_score,
            'reason': '; '.join(failures) if failures else 'all fixed gain, feasibility and runtime requirements met'}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--submission', type=Path, required=True)
    parser.add_argument('--split', choices=['public', 'hidden'], default='hidden')
    parser.add_argument('--output', type=Path, required=True)
    arguments = parser.parse_args()
    frozen_hash = verify_frozen_package()
    safe_tree(arguments.submission)
    policy = json.loads((ROOT / 'participant' / 'workspace' / 'policy.json').read_text())
    base = ROOT / ('participant/input' if arguments.split == 'public' else 'evaluator/hidden/cases')
    cases = json.loads((base / 'manifest.json').read_text())['cases']
    report_directory = arguments.output.resolve().parent
    report_directory.mkdir(parents=True, exist_ok=True)
    evidence = Path(tempfile.mkdtemp(prefix=arguments.output.stem + '_replay_', dir=report_directory))
    original_hashes = fingerprints(arguments.submission)
    snapshot = evidence / 'submission_snapshot'
    shutil.copytree(arguments.submission, snapshot, symlinks=True)
    safe_tree(snapshot)
    if fingerprints(snapshot) != original_hashes:
        raise ValueError('submission changed while taking the replay snapshot')
    rows = []
    for case in cases:
        directory = base / case['directory']
        atlas = Atlas.load(directory)
        case_evidence = evidence / case['id']
        case_evidence.mkdir()
        row = {'case_id': case['id'], 'family': case['family'], 'baseline_objective': atlas.metadata['baseline_objective']}
        try:
            result, runtime = replay(snapshot, ROOT / 'participant' / 'workspace', directory,
                                     case_evidence / 'output', policy['wall_seconds_per_case'])
            row['runtime'] = runtime
            if result is None:
                row.update(feasible=False, error=runtime['error'])
            else:
                row.update(validate_result(result, atlas))
                row['gain'] = 1 - row['objective'] / row['baseline_objective']
        except (ValueError, OSError, json.JSONDecodeError) as error:
            row.update(feasible=False, error=str(error))
        row['runtime_seconds'] = row.get('runtime', {}).get('wall_seconds', 0.0)
        row['core_score'] = row.get('gain')
        row['reason'] = row.get('error', 'feasible artifact scored' if row.get('feasible') else 'topology, acquisition, anchor, or admissibility constraint failed')
        rows.append(row)
        print(json.dumps(row, allow_nan=False), flush=True)
        report = {'verification_mode': 'A', 'split': arguments.split, 'policy': policy, 'cases': rows,
                  'completed': len(rows) == len(cases), 'evidence_directory': str(evidence),
                  'submission_sha256': original_hashes, 'frozen_manifest_sha256': frozen_hash}
        if report['completed']:
            report.update(aggregate(rows, policy))
        arguments.output.write_text(json.dumps(report, indent=2, allow_nan=False) + '\n')


if __name__ == '__main__':
    main()
