import os
os.environ['OPENBLAS_NUM_THREADS']='1'
os.environ['OMP_NUM_THREADS']='1'
import itertools
import time
import numpy as np
from blocks_search import powers,full_masks
from search import OUT,BETA,save,evaluate

def main():
    started=time.time()
    balanced=np.array([3,5,6,9,10,12])
    tasks=[((4,3,3,3,3),np.arange(16)),((2,)*8,balanced)]
    seen=set()
    for durations in sorted(set(itertools.permutations((4,4,3,3,2)))):
        canonical=min(durations[offset:]+durations[:offset] for offset in range(5))
        if canonical not in seen:
            seen.add(canonical)
            tasks.append((durations,np.arange(16)))
    tasks += [((3,3,3,3,2,2),np.arange(16)),((3,3,3,2,3,2),np.arange(16)),((3,3,2,3,3,2),np.arange(16))]
    tasks += [((4,2,2,2,2,2,2),balanced),((3,3,2,2,2,2,2),balanced)]
    for task,(durations,choices) in enumerate(tasks):
        dimensions=(len(choices),)*len(durations)
        total=len(choices)**len(durations)
        for start in range(0,total,8192):
            if (OUT/'witness.json').exists() or (OUT/'STOP_MULTIBLOCKS').exists():
                return
            sequences=choices[np.array(np.unravel_index(np.arange(start,min(start+8192,total)),dimensions)).T]
            product=np.broadcast_to(np.eye(4),(len(sequences),4,4)).copy()
            for block,duration in enumerate(durations):
                product=powers[duration][sequences[:,block]]@product
            sign=np.ones(len(product))
            for fugacity in [np.exp(BETA),np.exp(-BETA)]:
                sign*=np.linalg.slogdet(np.eye(4)+fugacity*product)[0]
            negative=np.flatnonzero(sign<0)
            if len(negative):
                sequence=sequences[negative[0]]
                fields=np.concatenate([np.repeat(full_masks[state][None],duration,axis=0) for state,duration in zip(sequence,durations)])
                print('FOUND',durations,sequence,'ratio',evaluate(fields),flush=True)
                save(fields)
                return
        print(f'{time.time()-started:.2f}s task={task} durations={durations} choices={len(choices)} total={total}',flush=True)

if __name__=='__main__':
    main()
