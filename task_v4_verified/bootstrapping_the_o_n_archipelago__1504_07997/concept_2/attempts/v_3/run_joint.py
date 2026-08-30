import os
os.environ['OPENBLAS_NUM_THREADS'] = '1'
os.environ['OMP_NUM_THREADS'] = '1'
os.environ['MKL_NUM_THREADS'] = '1'
import sys
sys.dont_write_bytecode = True
import json
import contextlib
import time
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor, as_completed
from joint_solver import Joint, ROOT, SOURCE

def recover(index):
    instances = json.loads(SOURCE.read_text())['instances']
    with (ROOT / ('joint_' + str(index) + '.log')).open('w', buffering=1) as log:
        with contextlib.redirect_stderr(log), contextlib.redirect_stdout(log):
            return Joint(instances[index]).recover(450)

if __name__ == '__main__':
    while (ROOT / 'joint_test.log').exists() and not (ROOT / 'joint_test.finished').exists():
        time.sleep(1)
    selected = list(map(int, sys.argv[1:])) or list(range(8))
    with ProcessPoolExecutor(max_workers=4) as pool:
        jobs = {pool.submit(recover, index): index for index in selected}
        for job in as_completed(jobs):
            answer = job.result()
            print('JOINT_COMPLETED', jobs[job], bool(answer), flush=True)
    from collect import collect
    collect()
