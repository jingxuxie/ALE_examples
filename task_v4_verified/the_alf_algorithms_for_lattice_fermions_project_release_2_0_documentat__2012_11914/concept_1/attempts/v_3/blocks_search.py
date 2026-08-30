import os
os.environ['OPENBLAS_NUM_THREADS'] = '1'
os.environ['OMP_NUM_THREADS'] = '1'
import json
import time
import numpy as np
from scipy.linalg import expm
from search import OUT, BETA, COUPLING, PROPAGATOR, save, evaluate

mapping = np.array([(site // 4 + site % 4) % 4 for site in range(16)])
masks = 2 * ((np.arange(16)[:,None] >> np.arange(4)[None]) & 1) - 1
full_masks = masks[:,mapping]
kinetic = np.array([[0,-2,0,-2],[-2,0,-2,0],[0,-2,0,-2],[-2,0,-2,0]])
propagator = expm(-BETA / 16 * kinetic)
matrices = propagator[None] * np.exp(COUPLING * masks[:,None,:])
powers = [np.broadcast_to(np.eye(4),(16,4,4)).copy()]
for duration in range(1,17):
    powers.append(matrices @ powers[-1])
sequences = np.array(np.unravel_index(np.arange(16**4), (16,)*4)).T

def main():
    started = time.time()
    best = 10
    durations_list = [(4,4,4,4),(3,4,5,4),(3,3,5,5),(3,5,3,5),(2,4,6,4),(3,4,4,5),(2,5,4,5),(2,3,6,5)]
    for first in range(1,14):
        for second in range(1,15-first):
            for third in range(1,16-first-second):
                fourth = 16 - first - second - third
                durations = (first,second,third,fourth)
                if durations not in durations_list:
                    durations_list.append(durations)
    for count,durations in enumerate(durations_list):
        if (OUT/'witness.json').exists() or (OUT/'STOP_BLOCKS').exists():
            return
        for start in range(0,len(sequences),2048):
            selected = sequences[start:start+2048]
            product = np.broadcast_to(np.eye(4),(len(selected),4,4)).copy()
            for block,duration in enumerate(durations):
                product = powers[duration][selected[:,block]] @ product
            sign = np.ones(len(product))
            for fugacity in [np.exp(BETA),np.exp(-BETA)]:
                sign *= np.linalg.slogdet(np.eye(4)+fugacity*product)[0]
            negative = np.flatnonzero(sign < 0)
            if len(negative):
                sequence = selected[negative[0]]
                fields = np.concatenate([np.repeat(full_masks[state][None],duration,axis=0) for state,duration in zip(sequence,durations)])
                print('FOUND',durations,sequence,'ratio',evaluate(fields),flush=True)
                save(fields)
                return
        print(f'{time.time()-started:.2f}s count={count} durations={durations}',flush=True)

if __name__ == '__main__':
    main()
