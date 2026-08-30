import os
os.environ['OPENBLAS_NUM_THREADS'] = '1'
import sys
import json
import time
import resource
import subprocess
from pathlib import Path
import policy
from test_policy import generate, Oracle, FAMILIES
from protocol import hello, query, answer, loads

def limits():
    resource.setrlimit(resource.RLIMIT_AS, (2*1024**3,2*1024**3))
    resource.setrlimit(resource.RLIMIT_CPU,(45,45))

if __name__ == '__main__':
    scratch = Path(__file__).parent/'scratch'
    scratch.mkdir(exist_ok=True)
    for offset,family in enumerate(FAMILIES):
        oracle = Oracle(generate(76432+offset,family),42686+offset)
        started = time.monotonic()
        process = subprocess.Popen([sys.executable,str(Path(__file__).parent/'policy.py')],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,bufsize=1,cwd=scratch,env={'PATH':'/usr/bin:/bin','OPENBLAS_NUM_THREADS':'1'},preexec_fn=limits)
        process.stdin.write(json.dumps(hello())+'\n')
        process.stdin.flush()
        last = time.monotonic()
        for index in range(73):
            line = process.stdout.readline()
            now = time.monotonic()
            assert now-last<15, 'message timeout'
            assert now-started<45, 'total timeout'
            last=now
            assert line.endswith('\n'), ('no message',process.stderr.read())
            message=loads(line)
            if message['type']=='answer':
                estimate,radii=answer(message)
                assert oracle.used==72
                process.wait(timeout=2)
                assert process.returncode==0
                assert process.stdout.read()==''
                print(family,'OK',round(time.monotonic()-started,3),'seconds',flush=True)
                break
            time_value,probe=query(message)
            response=oracle.measure(time_value,probe)
            process.stdin.write(json.dumps(response)+'\n')
            process.stdin.flush()
        else:
            raise RuntimeError('no answer')
