import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    findings = []
    for number in range(1, 4):
        concept = ROOT / f'concept_{number}'
        required = ['participant/TASK.md', 'participant/input', 'participant/workspace',
                    'participant/baseline', 'evaluator/evaluate.py', 'evaluator/hidden',
                    'attempts', 'champions', 'adversary', 'status.json']
        missing = [name for name in required if not (concept / name).exists()]
        status = json.loads((concept / 'status.json').read_text())
        audited_release = concept / 'adversary/audited_release.json'
        release_checks = None
        if audited_release.is_file():
            release = json.loads(audited_release.read_text())
            release_checks = {'manifest': str(audited_release.relative_to(ROOT)), 'mismatches': []}
            for name, expected in release['sha256'].items():
                path = concept / name
                if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != expected:
                    release_checks['mismatches'].append(name)
        frozen_checks = []
        for seal in sorted((concept / 'adversary').glob('frozen_generation_*.json')):
            frozen = json.loads(seal.read_text())
            generation = frozen['generation']
            snapshot = concept / 'adversary' / f'generation_{generation}_snapshot'
            base = snapshot if snapshot.is_dir() else concept
            mismatches = []
            for name, expected in frozen['sha256'].items():
                path = base / name
                if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != expected:
                    mismatches.append(name)
            frozen_checks.append({'generation': generation, 'mismatches': mismatches})
        attempts = []
        for record in sorted((concept / 'attempts').glob('v_*.run.json')):
            run = json.loads(record.read_text())
            log = record.with_name(record.name.replace('.run.json', '.runner.log')).read_text(errors='replace')
            session = re.search(r'^session id: (.+)$', log, re.MULTILINE)
            changed_submission = []
            submission = concept / 'attempts' / f"v_{run['attempt']}"
            for name, expected in run.get('submission_sha256', {}).items():
                path = submission / name
                if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != expected:
                    changed_submission.append(name)
            attempts.append({'file': record.name, 'attempt': run.get('attempt'),
                             'generation': run['generation'], 'status': run['status'],
                             'model_correct': run['model'] == 'ultima-alpha',
                             'one_hour_limit': run['authoring_limit_seconds'] == 3600,
                             'initially_empty': run['initial_output_empty'],
                             'participant_read_only': run['participant_read_only'],
                             'participant_unchanged': run.get('participant_unchanged'),
                             'actual_model_header': bool(re.search(r'^model: ultima-alpha$', log, re.MULTILINE)),
                             'session_id': session.group(1) if session else None,
                             'changed_submission_files': changed_submission,
                             'wall_seconds': run.get('wall_seconds')})
        escaping_links = []
        for path in (concept / 'participant').rglob('*'):
            if path.is_symlink():
                try:
                    path.resolve().relative_to((concept / 'participant').resolve())
                except ValueError:
                    escaping_links.append(str(path.relative_to(concept)))
        findings.append({'concept': concept.name, 'mode': status['mode'], 'missing': missing,
                         'frozen_checks': frozen_checks, 'attempts': attempts,
                         'audited_release': release_checks,
                         'escaping_participant_symlinks': escaping_links})
    report = {'built_concepts': len(findings), 'verification_modes': sorted({row['mode'] for row in findings}),
              'findings': findings}
    sessions = [attempt['session_id'] for row in findings for attempt in row['attempts']
                if attempt['session_id'] is not None]
    report['all_started_sessions_distinct'] = len(sessions) == len(set(sessions))
    report['all_finished_runs_valid'] = all(
        attempt['model_correct'] and attempt['one_hour_limit'] and attempt['initially_empty']
        and attempt['participant_read_only'] and attempt['participant_unchanged']
        and attempt['actual_model_header'] and attempt['wall_seconds'] <= 3616
        and not attempt['changed_submission_files']
        for row in findings for attempt in row['attempts'] if attempt['status'] != 'running')
    report['all_packages_integral'] = all(
        not row['missing'] and not row['escaping_participant_symlinks']
        and all(not seal['mismatches'] for seal in row['frozen_checks'])
        and (row['audited_release'] is None or not row['audited_release']['mismatches'])
        for row in findings)
    (ROOT / 'research/package_audit.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
