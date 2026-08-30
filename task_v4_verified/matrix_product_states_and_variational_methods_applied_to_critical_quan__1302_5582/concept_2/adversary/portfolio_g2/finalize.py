import os
import sys

sys.dont_write_bytecode = True
for variable in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS'):
    os.environ[variable] = '1'

import hashlib
import json
from pathlib import Path
import shutil
import subprocess
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parent
CONCEPT = ROOT.parents[1]


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + '\n')


def rank(record):
    return (int(record.get('passed', False)), record.get('worst_family_score', 0), record.get('core_score', 0))


def main():
    records = []
    for path in ROOT.glob('*/*.score.json'):
        record = json.loads(path.read_text())
        if record.get('valid') and (ROOT / record['artifact']).is_file():
            records.append(record)
    if not records:
        raise RuntimeError('No valid private checkpoint available')
    best = max(records, key=rank)
    shutil.copyfile(ROOT / best['artifact'], ROOT / 'state.npz')
    write_json(ROOT / 'selection.json', {'selected': best['artifact'], 'score': best,
                                       'criterion': 'valid, then passed, then worst-family score, then core score'})
    near_misses = [record for record in records if not record.get('passed')]
    if near_misses:
        near_miss = max(near_misses, key=rank)
        shutil.copyfile(ROOT / near_miss['artifact'], ROOT / 'near_miss.npz')
        write_json(ROOT / 'near_miss.score.json', near_miss)
    environment = dict(os.environ, PYTHONDONTWRITEBYTECODE='1', TMPDIR=str(ROOT / 'tmp'), XDG_CACHE_HOME=str(ROOT / 'cache'))
    command = [sys.executable, str(CONCEPT / 'evaluator' / 'evaluate.py'), '--submission', str(ROOT), '--output', str(ROOT / 'exact_checker_score.json')]
    completed = subprocess.run(command, cwd=ROOT, env=environment, capture_output=True, text=True, timeout=120)
    (ROOT / 'exact_checker_stdout.json').write_text(completed.stdout)
    (ROOT / 'exact_checker_stderr.log').write_text(completed.stderr)
    if completed.returncode:
        raise RuntimeError(f'Full evaluate.py returned {completed.returncode}')
    official = json.loads((ROOT / 'exact_checker_score.json').read_text())
    public_command = [sys.executable, str(CONCEPT / 'participant' / 'workspace' / 'check.py'), str(ROOT / 'state.npz')]
    public = subprocess.run(public_command, cwd=ROOT, env=environment, capture_output=True, text=True, timeout=120)
    (ROOT / 'public_checker_stdout.json').write_text(public.stdout)
    (ROOT / 'public_checker_stderr.log').write_text(public.stderr)
    manifest = json.loads((CONCEPT / 'adversary' / 'ratchet_2' / 'freeze_manifest.json').read_text())
    frozen = []
    for record in manifest['frozen_files']:
        actual = hashlib.sha256((CONCEPT / record['path']).read_bytes()).hexdigest()
        frozen.append({'path': record['path'], 'expected_sha256': record['sha256'], 'actual_sha256': actual, 'unchanged': actual == record['sha256']})
    write_json(ROOT / 'frozen_integrity.json', {'all_unchanged': all(record['unchanged'] for record in frozen), 'files': frozen})
    summary = {'completed_utc': datetime.now(timezone.utc).isoformat(), 'contract_version': 'critical-vacuum-v3',
               'selected_private_checkpoint': best['artifact'], 'state_sha256': hashlib.sha256((ROOT / 'state.npz').read_bytes()).hexdigest(),
               'official_evaluator_command': command, 'official_evaluator_result': official, 'public_checker_returncode': public.returncode,
               'frozen_files_unchanged': all(record['unchanged'] for record in frozen),
               'fresh_attempts_or_logs_read': False, 'generation_privileged_champion_source_reused': True,
               'independent_fresh_participant_attempt': False}
    write_json(ROOT / 'portfolio_results.json', summary)
    print(json.dumps(summary, indent=2), flush=True)
    if not summary['frozen_files_unchanged']:
        raise RuntimeError('Frozen file hash mismatch detected')


if __name__ == '__main__':
    main()
