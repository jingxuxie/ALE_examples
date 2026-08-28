import ast
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from collect_results import main as collect_results


ROOT = Path(__file__).resolve().parent.parent
REPOSITORY = ROOT.parent.parent


def load(path):
    return json.loads(path.read_text())


def digest(path):
    checksum = hashlib.sha256()
    with path.open('rb') as handle:
        for chunk in iter(lambda: handle.read(1024 ** 2), b''):
            checksum.update(chunk)
    return checksum.hexdigest()


def check_frozen(pilot):
    records = []
    for line in (pilot / 'private/public_frozen.sha256').read_text().splitlines():
        expected, name = line.split(maxsplit=1)
        path = Path(name)
        if not path.is_absolute():
            path = REPOSITORY / path
        path = path.resolve()
        actual = digest(path)
        if actual != expected:
            raise AssertionError(f'Frozen public artifact changed: {path}')
        records.append(str(path.relative_to(pilot)))
    return records


def scalar_refinement():
    pilot = ROOT / 'pilots/04_scalar_checkpoint'
    records = load(pilot / 'private/reference/refinement_audit.json')
    expected = set()
    for pool, folder in [('test', 'reference/cases'), ('challenge', 'challenge_pool')]:
        manifest = load(pilot / 'private' / folder / 'manifest.json')
        expected.update((pool, case['id']) for case in manifest['cases'] if case['operation'] != 'probe')
    actual = {(record['pool'], record['id']) for record in records}
    if actual != expected:
        raise AssertionError(f'Refinement incomplete: missing={sorted(expected - actual)}')
    groups = {}
    for comparison in ['100_vs_200', '100_vs_400', '200_vs_400']:
        values = [value['accuracy_score'] for record in records for value in record[comparison].values()]
        errors = [value['relative_error'] for record in records for value in record[comparison].values()]
        groups[comparison] = {
            'mean_transport_output_quality': float(np.mean(values)),
            'minimum_transport_output_quality': min(values),
            'maximum_relative_error': max(errors),
        }
    rechecks = {}
    for pool in ['test', 'challenge']:
        path = pilot / 'private' / f'refined_{pool}_report.json'
        report = load(path)
        if not report['diagnostic_only'] or report['reference_steps'] != 400:
            raise AssertionError(f'Refined-oracle diagnostic metadata is incorrect: {path}')
        rechecks[pool] = {
            'mean_core': report['score'],
            'worst_family': min(value['score'] for value in report['groups'].values()),
            'execution_failures': sum(case['status'] != 'ok' for case in report['cases']),
            'source': str(path.relative_to(ROOT)),
            'same_unchanged_submission': True,
        }
    return {'transport_cases': len(records), 'comparisons': groups,
            'frozen_submission_rechecks': rechecks,
            'interpretation': 'Author-reference discretization audit, not a fresh-model score or retroactive oracle change',
            'records': 'pilots/04_scalar_checkpoint/private/reference/refinement_audit.json'}


def main():
    collect_results()
    tournament = load(ROOT / 'private/tournament.json')
    audits = {}
    for pilot in sorted((ROOT / 'pilots').iterdir()):
        if not pilot.is_dir():
            continue
        frozen = check_frozen(pilot)
        exit_info = load(pilot / 'private/initial_exit.json')
        if exit_info['exit_code'] != 0:
            raise AssertionError(f'Fresh agent did not complete: {pilot.name}')
        checked_python = []
        for folder in [pilot / 'participant', pilot / 'attempt/initial']:
            for path in folder.rglob('*.py'):
                if 'runtime' not in path.relative_to(folder).parts:
                    ast.parse(path.read_text(), filename=str(path))
                    checked_python.append(str(path.relative_to(pilot)))
        ast.parse((pilot / 'private/evaluator.py').read_text())
        checked_npz = 0
        for folder in [pilot / 'private/reference', pilot / 'private/challenge_pool']:
            for path in folder.rglob('*.npz'):
                with np.load(path, allow_pickle=False) as archive:
                    for name in archive.files:
                        value = archive[name]
                        if value.dtype.kind in 'fci' and not np.isfinite(value).all():
                            raise AssertionError(f'Non-finite private array: {path}:{name}')
                checked_npz += 1
        public_runtime = pilot / 'participant/input/runtime'
        for forbidden in ['bijx', 'jaxlft', 'continuous_flow_lft']:
            if list(public_runtime.glob(f'lib/python*/site-packages/{forbidden}')):
                raise AssertionError(f'Private solution installed in runtime: {forbidden}')
        submission = {str(path.relative_to(pilot / 'attempt/initial')): digest(path)
                      for path in (pilot / 'attempt/initial').rglob('*')
                      if path.is_file() and '__pycache__' not in path.parts}
        audits[pilot.name] = {'frozen_public_files_checked': frozen,
                              'python_syntax_checked': checked_python,
                              'private_evaluator_sha256': digest(pilot / 'private/evaluator.py'),
                              'private_npz_archives_checked': checked_npz,
                              'initial_submission_sha256': submission,
                              'fresh_exit_code': exit_info['exit_code']}
    refinement = scalar_refinement()
    ranked = []
    for record in tournament['concepts']:
        ceiling = .95 if record['concept'].startswith('02_') else 1.
        ranked.append({'concept': record['concept'],
                       'initial_worst_family': record['initial']['worst_family'],
                       'exact_output_ceiling': ceiling,
                       'ceiling_relative_worst_family': record['initial']['worst_family'] / ceiling,
                       'initial_mean_core': record['initial']['mean_core'],
                       'fresh_seconds': record['attempt_seconds']})
    ranked.sort(key=lambda item: (item['ceiling_relative_worst_family'], item['initial_mean_core'] / item['exact_output_ceiling']))
    if any(record['initial']['mean_core'] < .9 for record in tournament['concepts']):
        raise AssertionError('Rejection rationale must be reviewed: an initial score is below solved threshold')
    selection = {
        'status': 'rejected', 'accepted_task': None,
        'completed_at_utc': datetime.now(timezone.utc).isoformat(),
        'target_paper': 'arXiv:2207.00283', 'model': 'ultima-alpha',
        'pilot_limit_seconds': 3600, 'concepts_built': 4,
        'scored_primary_attempts': 4, 'excluded_interrupted_prefix_attempts': 4,
        'candidate_directions': list('ABCDEFGH'),
        'candidate_inventory': 'private/candidate_gaps.md',
        'ranking_rule': 'Initial worst family relative to exact-output score ceiling, then relative mean; empirical runtime anchors retained separately',
        'hardest_first': ranked,
        'deeper_counterexample_search': [item['concept'] for item in ranked[:2]],
        'ratchets_per_concept': {item['concept']: 0 for item in ranked},
        'fresh_confirmation_attempts': 0,
        'confirmation_scores': None,
        'confirmation_not_run_reason': 'Both deeper searches fail the natural-counterexample gate; no valid ratcheted task exists',
        'reason_codes': ['ALL_FOUR_FROZEN_CONTRACTS_SOLVED', 'NO_SUBSTANTIVE_UNSOLVED_COMPONENT',
                         'NO_VALID_COUNTEREXAMPLE_REGION', 'SCALAR_CONTINUOUS_TARGET_QUALIFIED'],
        'scientific_limitations': ['Pilot01 does not enforce realistic adjoint-memory scaling',
                                   'Pilot03 uses a new restricted loop-potential adapter, not a released trained gauge network',
                                   'Pilot04 discloses 100-step answers while also naming the continuous IVP; refinement is not retroactive hardness'],
        'scalar_reference_refinement': refinement,
        'report': 'REPORT.md', 'scores': 'private/tournament.json',
        'launch_audit': 'private/LAUNCH_AUDIT.md',
    }
    (ROOT / 'selection.json').write_text(json.dumps(selection, indent=2) + '\n')
    (ROOT / 'private/final_audit.json').write_text(json.dumps({
        'completed_at_utc': selection['completed_at_utc'], 'status': 'passed',
        'public_trees_unchanged': True, 'initial_submissions_complete': True,
        'pilots': audits, 'scalar_refinement': refinement,
    }, indent=2) + '\n')
    collect_results()
    print(json.dumps({'status': selection['status'], 'hardest_first': [item['concept'] for item in ranked],
                      'scalar_refinement': refinement}, indent=2))


if __name__ == '__main__':
    main()
