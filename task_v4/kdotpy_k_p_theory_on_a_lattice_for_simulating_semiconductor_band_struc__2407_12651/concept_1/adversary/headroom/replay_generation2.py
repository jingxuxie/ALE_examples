import argparse
import hashlib
import json
import os
import shutil
import stat
import sys
import tempfile
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / 'participant' / 'workspace'))
sys.path.insert(0, str(ROOT / 'evaluator'))
from atlas import Atlas
from evaluate import aggregate, fingerprints, validate_result, verify_frozen_package
from isolation import replay, safe_tree

STRATEGIES = ('lp_round', 'lp_round_safe', 'lp_repair', 'lp_guided_search')


def read_small_json(path):
    descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(descriptor) as stream:
        information = os.fstat(stream.fileno())
        if not stat.S_ISREG(information.st_mode) or information.st_nlink != 1 or information.st_size > 65536:
            raise ValueError('not a bounded regular JSON artifact')
        return json.load(stream)


def numerical_fingerprints(cases_root):
    files = list(cases_root.rglob('*.json')) + list(cases_root.rglob('*.npz'))
    files += [ROOT / 'participant/workspace/atlas.py', ROOT / 'evaluator/evaluate.py', ROOT / 'evaluator/isolation.py']
    return {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest() for path in sorted(files)}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--submission', type=Path)
    parser.add_argument('--output-dir', type=Path)
    parser.add_argument('--single-strategy', action='store_true')
    parser.add_argument('--algorithm', default='LP-guided stochastic search with rounding checkpoints')
    arguments = parser.parse_args()
    started = time.monotonic()
    destination = arguments.output_dir.resolve() if arguments.output_dir else HERE / 'generation2'
    if not destination.resolve().is_relative_to(HERE.resolve()):
        raise SystemExit('private reports must remain under adversary/headroom')
    destination.mkdir(exist_ok=True)
    strategies = ('lp_guided_search',) if arguments.single_strategy else STRATEGIES
    policy = json.loads((ROOT / 'participant/workspace/policy.json').read_text())
    if (policy['mean_gain_min'], policy['worst_family_gain_min'], policy['minimum_case_gain'], policy['wall_seconds_per_case']) != (0.070, 0.057, 0.0, 90):
        raise SystemExit('requested generation-2 targets/runtime are not present')
    try:
        frozen_hash = verify_frozen_package()
        freeze_error = None
    except ValueError as error:
        frozen_hash = None
        freeze_error = str(error)
    cases_root = ROOT / 'evaluator/hidden/cases'
    cases = json.loads((cases_root / 'manifest.json').read_text())['cases']
    initial_hashes = numerical_fingerprints(cases_root)
    source = arguments.submission.resolve() if arguments.submission else HERE / 'submission'
    safe_tree(source)
    source_hashes = fingerprints(source)
    evidence = Path(tempfile.mkdtemp(prefix='isolated_replay_', dir=destination))
    snapshot = evidence / 'submission_snapshot'
    shutil.copytree(source, snapshot, symlinks=True)
    safe_tree(snapshot)
    if fingerprints(snapshot) != source_hashes:
        raise SystemExit('private solver changed during snapshot')
    rows = {strategy: [] for strategy in strategies}
    report = {'policy': policy, 'generation': 2, 'verification_mode': 'A', 'fresh_agent': False,
              'algorithm': arguments.algorithm,
              'private_control': True, 'frozen_manifest_sha256_at_start': frozen_hash,
              'frozen_manifest_error_at_start': freeze_error, 'source_sha256': source_hashes,
              'numerical_inputs_sha256': initial_hashes, 'evidence_directory': str(evidence),
              'runtime_accounting': 'Every phase receives the full enclosing replay wall time; checkpoints share the same successful isolated invocation, not separate reruns.',
              'complete': False, 'strategies': {}}
    for case in cases:
        if time.monotonic() - started > 705:
            break
        if numerical_fingerprints(cases_root) != initial_hashes:
            raise SystemExit('numerical code or hidden inputs changed during private replay')
        atlas = Atlas.load(cases_root / case['directory'])
        case_evidence = evidence / case['id']
        case_evidence.mkdir()
        runtime = {}
        returned = None
        error_message = None
        try:
            returned, runtime = replay(snapshot, ROOT / 'participant/workspace', cases_root / case['directory'], case_evidence / 'output', seconds=90)
        except (ValueError, OSError, json.JSONDecodeError) as error:
            error_message = str(error)
        for strategy in strategies:
            row = {'case_id': case['id'], 'family': case['family'], 'runtime': runtime,
                   'baseline_objective': atlas.metadata['baseline_objective']}
            try:
                if returned is None:
                    raise ValueError(error_message or runtime.get('error', 'isolated replay failed'))
                result = returned if strategy == 'lp_guided_search' else read_small_json(case_evidence / 'output' / (strategy + '.json'))
                row.update(validate_result(result, atlas))
                row['gain'] = 1 - row['objective'] / row['baseline_objective']
                row['core_score'] = row['gain']
                row['reason'] = 'feasible artifact scored' if row['feasible'] else 'feasibility constraint failed'
            except (ValueError, OSError, json.JSONDecodeError) as error:
                row.update(feasible=False, reason=str(error), error=str(error))
            row['runtime_seconds'] = runtime.get('wall_seconds', 0.0)
            rows[strategy].append(row)
            report['strategies'][strategy] = {'cases': rows[strategy], **aggregate(rows[strategy], policy)}
        report['complete'] = len(rows['lp_guided_search']) == len(cases)
        report['elapsed_seconds'] = time.monotonic() - started
        (destination / 'comparison.json').write_text(json.dumps(report, indent=2, allow_nan=False) + '\n')
        print(json.dumps({'case_id': case['id'], 'wall_seconds': runtime.get('wall_seconds'),
                          'strategies': {strategy: {'gain': rows[strategy][-1].get('gain'), 'feasible': rows[strategy][-1]['feasible']} for strategy in strategies}}, allow_nan=False), flush=True)
    report['numerical_inputs_unchanged'] = numerical_fingerprints(cases_root) == initial_hashes
    try:
        report['frozen_manifest_sha256_at_finish'] = verify_frozen_package()
        report['frozen_manifest_error_at_finish'] = None
    except ValueError as error:
        report['frozen_manifest_sha256_at_finish'] = None
        report['frozen_manifest_error_at_finish'] = str(error)
    (destination / 'comparison.json').write_text(json.dumps(report, indent=2, allow_nan=False) + '\n')
    final = {'generation': 2, 'complete': report['complete'], 'fresh_agents_launched': 0,
             'algorithm': arguments.algorithm,
             'fresh_outputs_inspected': False, 'root_files_changed_by_sidecar': False,
             'numerical_inputs_unchanged': report['numerical_inputs_unchanged'],
             'elapsed_seconds': report['elapsed_seconds'], 'evidence': str((destination / 'comparison.json').relative_to(HERE)),
             'strategies': {name: {key: value for key, value in data.items() if key != 'cases'} for name, data in report['strategies'].items()},
             'known_positive_control': report['complete'] and report['numerical_inputs_unchanged'] and report['strategies']['lp_guided_search']['passed'],
             'simple_lp_passes': report['complete'] and report['strategies'].get('lp_round', {}).get('passed', False),
             'lp_plus_single_site_repair_passes': report['complete'] and report['strategies'].get('lp_repair', {}).get('passed', False),
             'frozen_manifest_error_at_start': freeze_error,
             'frozen_manifest_error_at_finish': report['frozen_manifest_error_at_finish']}
    (destination / 'status.json').write_text(json.dumps(final, indent=2, allow_nan=False) + '\n')
    print(json.dumps(final, indent=2), flush=True)


if __name__ == '__main__':
    main()
