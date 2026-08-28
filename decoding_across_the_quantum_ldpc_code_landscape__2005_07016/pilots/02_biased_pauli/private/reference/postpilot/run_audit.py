import sys

sys.dont_write_bytecode = True

import hashlib
import json
import os
from pathlib import Path
import shutil

POSTPILOT = Path(__file__).resolve().parent
REFERENCE = POSTPILOT.parent
ROOT = REFERENCE.parents[1]
RESEARCH = ROOT.parents[1] / 'research'


def save_json(name, value):
    destination = POSTPILOT / name
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(value, indent=2, sort_keys=True) + '\n')


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def tree_digest(directory):
    result = {}
    for path in sorted(directory.rglob('*')):
        if path.is_symlink():
            raise ValueError(f'Unexpected symlink: {path}')
        if path.is_file():
            result[str(path.relative_to(directory))] = digest(path)
    return result


def protected_hashes():
    result = {name: tree_digest(ROOT / name) for name in
              ('participant', 'attempt', 'private/challenge_pool')}
    result['reference_upstream'] = tree_digest(REFERENCE / 'upstream')
    result['reference_codes'] = tree_digest(REFERENCE / 'codes')
    files = [ROOT / 'private' / 'evaluator.py', RESEARCH / 'isolation.py',
             RESEARCH / 'sources' / 'bp_osd' / 'src' / 'bposd' / 'css_decode_sim.py',
             REFERENCE / 'evidence' / 'fresh_pilot.json']
    files.extend(REFERENCE / name for name in ('bootstrap.py', 'geometry.py', 'solve.py',
        'build.py', 'isolation.py', 'audit.py', 'provenance.json', 'participant_manifest.json',
        'requirements.txt', 'design.md', 'README.md'))
    files.extend(sorted((RESEARCH / 'sources' / 'bias_tailored_qldpc' / 'parity_check_matrices').glob('*.txt')))
    result['protected_files'] = {str(path): digest(path) for path in files}
    return result


def main():
    if (POSTPILOT / 'challenge_report.json').exists():
        raise FileExistsError('Bounded audit already ran; refusing an outcome-selective rerun')
    before = protected_hashes()
    save_json('hashes_before.json', before)
    submission = POSTPILOT / 'submission_snapshot'
    if submission.exists():
        if tree_digest(submission) != before['attempt']:
            raise ValueError('Existing audit snapshot is not the unchanged submission')
    else:
        shutil.copytree(ROOT / 'attempt', submission)
    assert tree_digest(submission) == before['attempt']
    sys.path.insert(0, str(ROOT / 'private'))
    sys.path.insert(0, str(REFERENCE))
    import evaluator
    import bootstrap
    import isolation

    bootstrap.REFERENCE = POSTPILOT
    os.environ['MPLCONFIGDIR'] = str(POSTPILOT / '.cache' / 'matplotlib')
    os.environ['XDG_CACHE_HOME'] = str(POSTPILOT / '.cache')
    original_runner = isolation.run_submission
    observed = []

    def retaining_runner(*args, **kwargs):
        result = original_runner(*args, **kwargs)
        input_path = Path(args[2])
        record = {name: value for name, value in result.items() if name != 'answer_bytes'}
        record.update(input_sha256=digest(input_path), case=input_path.name)
        if result['answer_bytes'] is not None:
            destination = POSTPILOT / 'predictions' / input_path.name
            destination.parent.mkdir(exist_ok=True)
            destination.write_bytes(result['answer_bytes'])
            record['prediction_sha256'] = digest(destination)
        observed.append(record)
        save_json('isolation_runs.json', observed)
        if result['returncode'] != 0 and 'bwrap:' in result.get('stderr', ''):
            raise RuntimeError('Isolation infrastructure failed; no decoding result was scored')
        return result

    isolation.run_submission = retaining_runner
    original_arguments = sys.argv[:]
    sys.argv = [str(ROOT / 'private' / 'evaluator.py'), '--submission', str(submission),
                '--report', str(POSTPILOT / 'challenge_report.json'), '--split', 'challenge']
    failure = None
    try:
        evaluator.main()
    except BaseException as error:
        failure = repr(error)
        raise
    finally:
        sys.argv = original_arguments
        isolation.run_submission = original_runner
        after = protected_hashes()
        save_json('hashes_after.json', after)
        provenance = dict(protected_originals_unchanged=before == after,
            snapshot_matches_original_before=tree_digest(submission) == before['attempt'],
            original_submission=str(ROOT / 'attempt'), evaluated_submission=str(submission),
            evaluator_sha256=digest(ROOT / 'private' / 'evaluator.py'),
            isolation_sha256=digest(REFERENCE / 'isolation.py'),
            instrumentation='Existing evaluator.main and runner; retain answer bytes; temporary root relocated only',
            scoring_contract_unchanged=True, split='existing frozen challenge',
            new_cases_created=False, fresh_models_launched=False, failure=failure)
        save_json('execution_provenance.json', provenance)
        if before != after:
            raise AssertionError('A protected original changed during audit; inspect hash ledgers')


if __name__ == '__main__':
    main()
