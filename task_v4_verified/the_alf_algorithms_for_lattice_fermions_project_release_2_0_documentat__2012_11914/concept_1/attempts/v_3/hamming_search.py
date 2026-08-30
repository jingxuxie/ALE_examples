import os
os.environ['OPENBLAS_NUM_THREADS'] = '1'
os.environ['OMP_NUM_THREADS'] = '1'
import itertools
import json
import time
import numpy as np
from search import OUT, BETA, COUPLING, save, evaluate
from blocks_search import mapping, propagator

def main():
    started = time.time()
    full = np.array(json.loads((OUT/'structured_best.json').read_text())['fields'],dtype=np.int8)
    base = full[:,:4].reshape(64)
    for distance in range(1,8):
        combinations = itertools.combinations(range(64),distance)
        count = 0
        while True:
            if (OUT/'witness.json').exists() or (OUT/'STOP_HAMMING').exists():
                return
            chunk = list(itertools.islice(combinations,8192))
            if not chunk:
                break
            flips = np.array(chunk)
            fields = np.repeat(base[None],len(chunk),axis=0)
            fields[np.arange(len(chunk))[:,None],flips] *= -1
            fields = fields.reshape(-1,16,4)
            product = np.broadcast_to(np.eye(4),(len(fields),4,4)).copy()
            for time_index in range(16):
                product = propagator @ (np.exp(COUPLING*fields[:,time_index,:,None])*product)
            signs = np.ones(len(fields))
            for fugacity in [np.exp(BETA),np.exp(-BETA)]:
                signs *= np.linalg.slogdet(np.eye(4)+fugacity*product)[0]
            negatives = np.flatnonzero(signs<0)
            if len(negatives):
                full = fields[negatives[0]][:,mapping]
                print('FOUND distance',distance,'flips',flips[negatives[0]],'ratio',evaluate(full),flush=True)
                save(full)
                return
            count += len(chunk)
        print(f'{time.time()-started:.2f}s distance={distance} count={count}',flush=True)

if __name__ == '__main__':
    main()
