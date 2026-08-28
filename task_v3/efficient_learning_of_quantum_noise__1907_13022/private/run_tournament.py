import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import hashlib
import json
import os
from pathlib import Path
import signal
import shutil
import subprocess
import time


ROOT = Path(__file__).resolve().parent.parent
RUNNER = ROOT.parents[1] / 'run_allowlisted_codex.sh'


def fingerprints(directory):
    return {str(path.relative_to(directory)):hashlib.sha256(path.read_bytes()).hexdigest()
            for path in sorted(directory.rglob('*')) if path.is_file()}


def run_one(concept, phase, participant_version, limit):
    directory = ROOT / concept
    participant = directory / participant_version
    attempt = directory / ('attempt' if phase == 'pilot' else f'attempt_{phase}')
    attempt.mkdir(exist_ok=True)
    if any(attempt.iterdir()):
        raise RuntimeError(f'Fresh output directory is not empty: {attempt}')
    logs = ROOT / 'private' / 'runs' / phase
    logs.mkdir(parents=True, exist_ok=True)
    hashes = fingerprints(participant)
    private_hashes = fingerprints(directory/'private')
    prompt = (f'Read TASK.md and input/FORMAT.md if present. Complete the task autonomously. '
              f'Write your final reusable, self-contained solver.py and development files only to {attempt}. '
              f'The evaluator stages only your final solver.py, not development helpers. '
              f'The task directory is read-only. You have at most {limit} seconds. '
              f'Use installed numerical tools and test your implementation; do not stop at a plan. '
              f'Only the task directory and your output directory are available. '
              f'Do not seek other tasks, hidden references, or earlier attempts.')
    command = [str(RUNNER), '--model', 'ultima-alpha', '--effort', 'xhigh', '--task-read-only',
               str(participant), str(attempt), prompt]
    started = time.monotonic()
    started_utc = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
    timed_out = False
    with (logs/f'{concept}.log').open('w') as stream:
        process = subprocess.Popen(command, stdout=stream, stderr=subprocess.STDOUT,
                                   start_new_session=True, env=dict(os.environ,OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1'))
        try:
            returncode = process.wait(timeout=limit)
        except subprocess.TimeoutExpired:
            timed_out = True
            os.killpg(process.pid,signal.SIGTERM)
            try:
                returncode = process.wait(timeout=20)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid,signal.SIGKILL)
                returncode = process.wait()
    result = dict(concept=concept, phase=phase, model='ultima-alpha', reasoning_effort='xhigh',
                  started_utc=started_utc, seconds=time.monotonic()-started, limit_seconds=limit,
                  returncode=returncode,timed_out=timed_out,participant=str(participant),attempt=str(attempt),
                  participant_unchanged=hashes==fingerprints(participant),participant_sha256=hashes,
                  private_sha256_before_attempt=private_hashes,
                  solver_exists=(attempt/'solver.py').is_file(),command=command)
    if result['solver_exists']:
        frozen = logs/'submissions'
        frozen.mkdir(exist_ok=True)
        shutil.copy2(attempt/'solver.py',frozen/f'{concept}.py')
        result['submission_sha256'] = hashlib.sha256((frozen/f'{concept}.py').read_bytes()).hexdigest()
    (logs/f'{concept}.json').write_text(json.dumps(result,indent=2)+'\n')
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('concepts',nargs='+')
    parser.add_argument('--phase',default='pilot')
    parser.add_argument('--participant',default='participant')
    parser.add_argument('--limit',type=int,default=3600)
    args = parser.parse_args()
    with ThreadPoolExecutor(max_workers=len(args.concepts)) as executor:
        futures = [executor.submit(run_one,concept,args.phase,args.participant,args.limit) for concept in args.concepts]
        for future in as_completed(futures):
            result = future.result()
            print(json.dumps({key:result[key] for key in ['concept','phase','returncode','seconds','solver_exists','timed_out']}),flush=True)


if __name__ == '__main__':
    main()
