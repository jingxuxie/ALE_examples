import argparse
import ctypes
import time
import numpy as np
import fermion
from search import Engine, LIB, INT, DOUBLE


LIB.block_bases.argtypes=[ctypes.c_int,INT,DOUBLE,DOUBLE,DOUBLE,ctypes.c_int,ctypes.c_int,DOUBLE,DOUBLE]
LIB.block_maxima_fast.argtypes=[DOUBLE,DOUBLE,DOUBLE,DOUBLE]
parser=argparse.ArgumentParser()
parser.add_argument('--case',type=int,default=0)
parser.add_argument('--seconds',type=float,default=300)
parser.add_argument('--choices',type=int,default=60)
args=parser.parse_args()
engine=Engine(fermion.load_cases()[args.case])
engine.best=engine.load()[2]
iteration=0
while time.time()-engine.started<args.seconds:
    iteration+=1
    labels,angles,loss=engine.load()
    choices=[]
    for position in range(len(labels)+1):
        trial_labels=np.insert(labels,position,[0,0]);trial_angles=np.insert(angles,position,[0.,0.])
        left,right=np.empty((750,100)),np.empty((750,100))
        LIB.block_bases(len(trial_labels),trial_labels,trial_angles,engine.initial,engine.target,position,position+1,left,right)
        matrix=np.ascontiguousarray(left@right.T)
        values,aa,bb=np.empty((250,250)),np.empty((250,250)),np.empty((250,250))
        LIB.block_maxima_fast(matrix,values,aa,bb)
        for flat in np.argpartition(values.ravel(),-100)[-100:]:
            first,second=np.unravel_index(flat,values.shape)
            choices.append((values[first,second],position,first,second,aa[first,second],bb[first,second]))
    choices.sort(reverse=True)
    seen=set();improved=False;tried=0
    for value,position,first,second,first_angle,second_angle in choices:
        trial_labels=np.insert(labels,position,[first,second]);trial_angles=np.insert(angles,position,[first_angle,second_angle])
        state,_=engine.state_jac(trial_labels,trial_angles)
        fingerprint=np.round(state,6).tobytes()
        if fingerprint in seen:continue
        seen.add(fingerprint);tried+=1
        grown=engine.optimize(trial_labels,trial_angles,200)
        deletions=[]
        for removed in range(len(grown[0])):
            deletions.append(engine.optimize(np.delete(grown[0],removed),np.delete(grown[1],removed),200))
        deletions.sort(key=lambda entry:entry[2])
        candidates=[]
        for shorter in deletions[:4]:
            if shorter[2]>engine.best+1e-6:continue
            for removed in range(len(shorter[0])):
                candidates.append(engine.optimize(np.delete(shorter[0],removed),np.delete(shorter[1],removed),200))
        if candidates:
            candidate=min(candidates,key=lambda entry:entry[2])
            if candidate[2]<engine.best-1e-10:
                engine.save(*candidate)
                improved=True
                break
        if tried%10==0:
            print('pair trial',iteration,tried,'grown',grown[2],'best',engine.best,'elapsed',time.time()-engine.started,flush=True)
        if tried>=args.choices or time.time()-engine.started>=args.seconds:break
    print('pair round',iteration,'improved',improved,'best',engine.best,'elapsed',time.time()-engine.started,flush=True)
    if not improved:break
