import os
os.environ['OPENBLAS_NUM_THREADS'] = '1'
os.environ['OMP_NUM_THREADS'] = '1'
os.environ['MKL_NUM_THREADS'] = '1'
os.environ['NUMEXPR_NUM_THREADS'] = '1'
os.environ['PYTHONDONTWRITEBYTECODE'] = '1'
import sys
sys.dont_write_bytecode = True
import json
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor, as_completed
import contextlib

ROOT = Path(__file__).resolve().parent
SOURCE = Path('/srv/home/xuandong/mnt/jingxu/ALE/tasks_v4/bootstrapping_the_o_n_archipelago__1504_07997/concept_2/participant/input/instances.json')
sys.path.insert(0, str(SOURCE.parent.parent / 'baseline'))

def recover(instance):
    import pipeline
    directory = ROOT / 'baseline_work' / instance['id']
    directory.mkdir(parents=True, exist_ok=True)
    with (directory / 'run.log').open('w', buffering=1) as log:
        with contextlib.redirect_stderr(log), contextlib.redirect_stdout(log):
            answer = pipeline.recover(instance, 300, SOURCE, directory)
    (directory / 'answer.json').write_text(json.dumps({'cases': [answer]}, indent=2))
    return answer

if __name__ == '__main__':
    instances = json.loads(SOURCE.read_text())['instances']
    cases = {}
    with ProcessPoolExecutor(max_workers=4) as pool:
        jobs = {pool.submit(recover, instance): instance['id'] for instance in instances}
        for job in as_completed(jobs):
            answer = job.result()
            cases[answer['id']] = answer
            destination = {'cases': [cases[instance['id']] for instance in instances if instance['id'] in cases]}
            (ROOT / 'answer.json').write_text(json.dumps(destination, indent=2))
            print('COMPLETED', answer['id'], flush=True)
