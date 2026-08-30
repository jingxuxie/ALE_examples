import datetime
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import time

import numpy as np

root=Path(__file__).resolve().parent
expected=np.asarray(json.loads((root/'../../participant/input/target.json').read_text())['cyclic_autocorrelation'],dtype=np.int64)
best_cost=float('inf')
best_values=None

def select_best():
    global best_cost,best_values
    for path in root.glob('*.json'):
        try:
            raw=json.loads(path.read_text())['a']
            if len(raw)!=4096 or any(type(value) is not int or value not in (0,1,2) for value in raw):
                continue
            values=np.asarray(raw,dtype=np.int64)
            if not np.array_equal(np.bincount(values,minlength=3),[3328,512,256]) or np.any(values*np.roll(values,1)):
                continue
            residual=np.rint(np.fft.irfft(abs(np.fft.rfft(values))**2,n=4096)).astype(np.int64)-expected
            cost=int(residual@residual)
            if cost<best_cost:
                best_cost=cost
                best_values=values.tolist()
                print('BEST',best_cost,path.name,flush=True)
        except (OSError,ValueError,KeyError,TypeError):
            continue
    if best_values is not None:
        temporary=root/'design.tmp'
        temporary.write_text(json.dumps({'schema_version':1,'a':best_values},separators=(',',':'))+'\n')
        temporary.replace(root/'design.json')

deadline=datetime.datetime.fromisoformat('2026-08-28T12:05:55+00:00').timestamp()
while True:
    select_best()
    remaining=deadline-time.time()
    if best_cost==0 or remaining<=0:
        break
    time.sleep(min(10,remaining))

roots={int(value) for value in sys.argv[1:]}
for process in roots:
    try:os.kill(process,signal.SIGSTOP)
    except ProcessLookupError:pass
table=subprocess.check_output(['ps','-eo','pid=,ppid='],text=True)
parents={int(line.split()[0]):int(line.split()[1]) for line in table.splitlines()}
processes=set(roots)
while True:
    expanded=processes|{process for process,parent in parents.items() if parent in processes}
    if expanded==processes:break
    processes=expanded
processes.discard(os.getpid())
for process in processes:
    try:
        os.kill(process,signal.SIGTERM)
        os.kill(process,signal.SIGCONT)
    except ProcessLookupError:pass
time.sleep(0.5)
select_best()
checked=subprocess.run([sys.executable,str(root/'../../participant/check.py'),str(root)],text=True,capture_output=True,check=True)
print(checked.stdout,flush=True)
if checked.stderr:print(checked.stderr,flush=True)
for path in root.iterdir():
    if path.name=='design.json':continue
    if path.is_dir() and not path.is_symlink():shutil.rmtree(path)
    else:path.unlink()
print('FINAL ARTIFACT',root/'design.json','BYTES',(root/'design.json').stat().st_size,flush=True)
