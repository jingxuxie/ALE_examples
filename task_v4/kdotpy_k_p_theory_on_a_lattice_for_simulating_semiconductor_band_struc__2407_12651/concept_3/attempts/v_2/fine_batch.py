import os
os.environ['OPENBLAS_NUM_THREADS'] = '1'
os.environ['OMP_NUM_THREADS'] = '1'
import json
import subprocess
from pathlib import Path
from multiprocessing import Pool

def run_job(index):
    output = f'pair_fine_{index}.json'
    with open(f'pair_fine_{index}.log', 'w') as log:
        subprocess.run(['python', 'fine.py', f'pair_{index}.json', '--output', output, '--rounds', '8'], stdout=log, stderr=subprocess.STDOUT, check=True)
    stats = json.loads(Path(output+'.stats').read_text())
    return index, stats

if __name__ == '__main__':
    with Pool(3) as pool:
        for index, stats in pool.imap_unordered(run_job, range(6, 20)):
            print(index, stats, flush=True)
