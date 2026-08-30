from synth import *
import multiprocessing as mp

LIB.support_size.argtypes=[ctypes.c_int,INTS]
LIB.support_size.restype=ctypes.c_int
LIB.support_choices.argtypes=[FLOATS,ctypes.c_int,INTS]
LIB.support_choices.restype=ctypes.c_int
LIB.support_advance.argtypes=[FLOATS,ctypes.c_int]
WORKER=None
HF=None

def initialize():
    global WORKER,HF
    WORKER=Engine(0)
    occupied={orbital for orbital in range(10) if WORKER.case.reference_mask>>orbital&1}
    HF=np.array([index for index,label in enumerate(WORKER.labels) if set(label.annihilate)<=occupied and not set(label.create)&occupied])

def batch(job):
    mode,seeds=job
    best=(1.0,None,None,None,mode)
    tested=0
    for seed in seeds:
        rng=np.random.default_rng(seed)
        if mode==0:labels=rng.choice(250,size=24,replace=False).astype(np.int32);raw=rng.random(24)
        elif mode==1:labels=rng.integers(250,size=24,dtype=np.int32);raw=rng.random(24)
        elif mode==2:
            pairs=[(int(rng.integers(250)),rng.random()) for position in range(24)]
            labels=np.array([pair[0] for pair in pairs],dtype=np.int32);raw=np.array([pair[1] for pair in pairs])
        elif mode==3:labels=rng.choice(HF,size=24,replace=False).astype(np.int32);raw=rng.random(24)
        elif mode==4:labels=rng.choice(HF,size=24,replace=True).astype(np.int32);raw=rng.random(24)
        else:
            support=WORKER.reference.copy();candidates=np.empty(250,dtype=np.int32);chosen=[];parameters=[]
            for position in range(24):
                count=LIB.support_choices(support,0 if mode in (5,6) else mode-6,candidates)
                if count==0:count=LIB.support_choices(support,0,candidates)
                pool=candidates[:count]
                if mode==6:pool=np.array([label for label in pool if label not in chosen])
                label=int(pool[int(rng.integers(len(pool)))])
                chosen.append(label);parameters.append(rng.random());LIB.support_advance(support,label)
            labels=np.array(chosen,dtype=np.int32);raw=np.array(parameters)
        if LIB.support_size(24,labels)<100:continue
        tested+=1
        starts=[]
        for offset,scale in [(-1.2,2.4),(-np.pi,2*np.pi),(0.25,1.0),(0.4,0.8)]:
            angles=offset+scale*raw
            state=WORKER.state(labels,angles)
            if state@WORKER.target<0:angles[0]+=np.pi
            cost=0.5*np.sum((WORKER.state(labels,angles)-WORKER.target)**2)
            starts.append((cost,angles))
        cost,angles=min(starts,key=lambda entry:entry[0])
        value,angles=WORKER.optimize(labels.tolist(),angles,iterations=90)
        if value<0.08:value,angles=WORKER.optimize(labels.tolist(),angles,iterations=500,precise=True)
        if value<best[0]:best=(value,labels.tolist(),angles,int(seed),mode)
    return best,tested,len(seeds)

def run(seconds=360):
    engine=Engine(0)
    common=[210606850,21060685,2106068,314159,271828,161803,1234567,987654321,424242,8675309,20260628,20260828,20250828]
    common.extend(range(20250301,20250332));common.extend(range(20260301,20260332));common.extend(range(20260801,20260832))
    tasks=[(mode,common) for mode in range(9)]
    tasks.extend((mode,list(range(first,first+200))) for first in range(0,100000,200) for mode in range(9))
    deadline=time.time()+seconds
    best=1.0;tested=0;seeds=0
    with mp.Pool(40,initializer=initialize) as pool:
        for result,valid,count in pool.imap_unordered(batch,tasks,chunksize=1):
            tested+=valid;seeds+=count
            if result[0]<best:
                best=result[0]
                print('SEEDBEST',best,'seed',result[3],'mode',result[4],'tested',tested,'seeds',seeds,'time',time.time()-engine.started,flush=True)
                engine.save(result[1],result[2],result[0])
                if best<1e-10:engine.save(result[1],result[2],best,tag='seed_exact');break
            if time.time()>deadline:break
    print('SEEDS_DONE',best,tested,seeds,time.time()-engine.started,flush=True)

if __name__=='__main__':run()
