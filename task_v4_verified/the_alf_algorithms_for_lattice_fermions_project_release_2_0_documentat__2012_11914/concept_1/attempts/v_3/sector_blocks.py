import os
os.environ['OPENBLAS_NUM_THREADS']='1'
os.environ['OMP_NUM_THREADS']='1'
import sys
import time
import itertools
import numpy as np
from scipy.linalg import expm
from search import OUT,BETA,COUPLING,KINETIC,save,evaluate

mode=int(sys.argv[1])
generators=[(7,9),(7,8),(3,5)][mode]
subgroup=[0,generators[0],generators[1],generators[0]^generators[1]]
gray=[0,1,3,2]
labels=np.array([gray[site//4]+4*gray[site%4] for site in range(16)])
representatives,mapping=np.unique(np.min(labels[:,None]^np.array(subgroup)[None],axis=1),return_inverse=True)
kinetics=[]
for character in range(4):
    basis=np.zeros((16,4))
    for group,representative in enumerate(representatives):
        for index,element in enumerate(subgroup):
            source=int(np.flatnonzero(labels==(representative^element))[0])
            parity=((character&index).bit_count()%2)
            basis[source,group]=(-1)**parity/2
    kinetics.append(basis.T@KINETIC@basis)
propagators=np.array([expm(-BETA/16*kinetic) for kinetic in kinetics])
masks=2*((np.arange(16)[:,None]>>np.arange(4)[None])&1)-1
matrices=propagators[None]*np.exp(COUPLING*masks[:,None,None,:])
powers=[np.broadcast_to(np.eye(4),(16,4,4,4)).copy()]
for duration in range(1,17):
    powers.append(matrices@powers[-1])

def main():
    started=time.time()
    balanced=np.array([3,5,6,9,10,12])
    tasks=[((4,4,4,4),np.arange(16)),((3,4,5,4),np.arange(16)),((4,3,3,3,3),np.arange(16)),((2,)*8,balanced)]
    tasks += [(durations,np.arange(16)) for durations in [(3,3,5,5),(3,5,3,5),(2,4,6,4),(3,4,4,5),(2,5,4,5),(2,3,6,5)]]
    tasks += [((3,3,3,3,2,2),np.arange(16)),((3,3,2,3,3,2),np.arange(16))]
    seen=set(durations for durations,choices in tasks if len(durations)==4)
    for first in range(1,14):
        for second in range(1,15-first):
            for third in range(1,16-first-second):
                durations=(first,second,third,16-first-second-third)
                canonical=min(durations[offset:]+durations[:offset] for offset in range(4))
                if canonical not in seen:
                    seen.add(canonical)
                    tasks.append((durations,np.arange(16)))
    for task,(durations,choices) in enumerate(tasks):
        total=len(choices)**len(durations)
        dimensions=(len(choices),)*len(durations)
        for start in range(0,total,4096):
            if (OUT/'witness.json').exists() or (OUT/'STOP_SECTORS').exists():
                return
            sequences=choices[np.array(np.unravel_index(np.arange(start,min(start+4096,total)),dimensions)).T]
            product=np.broadcast_to(np.eye(4),(len(sequences),4,4,4)).copy()
            for block,duration in enumerate(durations):
                product=powers[duration][sequences[:,block]]@product
            signs=np.ones(len(product))
            for fugacity in [np.exp(BETA),np.exp(-BETA)]:
                signs*=np.prod(np.linalg.slogdet(np.eye(4)+fugacity*product)[0],axis=1)
            negative=np.flatnonzero(signs<0)
            if len(negative):
                sequence=sequences[negative[0]]
                fields=np.concatenate([np.repeat(masks[state][None],duration,axis=0) for state,duration in zip(sequence,durations)])[:,mapping]
                print('FOUND',durations,sequence,'ratio',evaluate(fields),flush=True)
                save(fields)
                return
        print(f'{time.time()-started:.2f}s task={task} durations={durations} choices={len(choices)} total={total}',flush=True)

if __name__=='__main__':
    main()
