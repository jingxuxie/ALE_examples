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
parser.add_argument('--beam',type=int,default=20)
parser.add_argument('--choices',type=int,default=12)
args=parser.parse_args()
engine=Engine(fermion.load_cases()[args.case])
engine.best=engine.load()[2]
beam=[(np.empty(0,np.int32),np.empty(0),2.0)]
for step in range(engine.case.max_gates//2):
    trials=[]
    for labels,angles,loss in beam:
        choices=[]
        for position in range(len(labels)+1):
            trial_labels=np.insert(labels,position,[0,0])
            trial_angles=np.insert(angles,position,[0.0,0.0])
            left,right=np.empty((750,100)),np.empty((750,100))
            LIB.block_bases(len(trial_labels),trial_labels,trial_angles,engine.initial,engine.target,position,position+1,left,right)
            matrix=np.ascontiguousarray(left@right.T)
            values,aa,bb=np.empty((250,250)),np.empty((250,250)),np.empty((250,250))
            LIB.block_maxima_fast(matrix,values,aa,bb)
            top=np.argpartition(values.ravel(),-100)[-100:]
            for flat in top:
                first,second=np.unravel_index(flat,values.shape)
                choices.append((values[first,second],position,first,second,aa[first,second],bb[first,second]))
        choices.sort(reverse=True)
        fingerprints=set()
        for value,position,first,second,first_angle,second_angle in choices:
            trial_labels=np.insert(labels,position,[first,second])
            trial_angles=np.insert(angles,position,[first_angle,second_angle])
            state,_=engine.state_jac(trial_labels,trial_angles)
            fingerprint=np.round(state,6).tobytes()
            if fingerprint in fingerprints:
                continue
            fingerprints.add(fingerprint)
            trial=engine.optimize(trial_labels,trial_angles,200)
            trials.append(trial)
            if len(fingerprints)>=args.choices:
                break
    trials.sort(key=lambda trial:trial[2])
    kept=[]
    fingerprints=set()
    for trial in trials:
        state,_=engine.state_jac(trial[0],trial[1])
        fingerprint=np.round(state,5).tobytes()
        if fingerprint in fingerprints:
            continue
        fingerprints.add(fingerprint)
        kept.append(trial)
        if len(kept)>=args.beam:
            break
    beam=kept
    print('dual',2*(step+1),'best',beam[0][2],'worst',beam[-1][2],'size',len(beam),'elapsed',time.time()-engine.started,flush=True)
for position,item in enumerate(beam):
    engine.save(*item)
    engine.save(*item,suffix='dual_'+str(position))
