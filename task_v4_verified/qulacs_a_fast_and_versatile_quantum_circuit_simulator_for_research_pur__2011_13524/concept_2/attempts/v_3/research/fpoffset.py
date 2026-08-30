import numpy as np,sys,random,time,json
kind=sys.argv[1];NN=int(sys.argv[2]);offs=np.arange(0,241);ph=np.array([np.angle(np.linalg.slogdet(np.load('unitary_%dq.npy'%n))[0])/(2*np.pi) for n in [7,8]]);ks=[np.array(sorted(set(list(range(79,128,2))+[7*k for k in range(10,31)]))),np.array(sorted(set(list(range(106,169,2))+[8*k for k in range(10,31)])))];seeds=list(range(NN))+[y*10000+m*100+d for y in range(2015,2028) for m in range(1,13) for d in range(1,32)]+[0xDEADBEEF,0xC0FFEE,0xBAD5EED,0x12345678,0xCAFEBABE,123456789,1234567890,3141592,8675309,201113524];start=time.time();best=1
for j,seed in enumerate(seeds):
 if kind=='python':r=random.Random(seed);u=np.array([r.random() for _ in range(1000)])
 elif kind=='legacy':u=np.random.RandomState(seed).random(1000)
 else:u=np.random.default_rng(seed).random(1000)
 for rem in range(3):
  mask=np.arange(1000)%3!=rem;cs=np.r_[0,np.cumsum(u*mask)];os=offs[offs%3==rem]
  for ni,n in enumerate([7,8]):
   vals=(cs[os[:,None]+3*ks[ni]]-cs[os[:,None]])*(2**(n-1))
   for div in [1,2]:
    v=vals/div-ph[ni];ds=np.abs(v-np.rint(v));a,b=np.unravel_index(ds.argmin(),ds.shape)
    if ds[a,b]<best:best=ds[a,b];print('best',best,kind,seed,n,int(os[a]),int(ks[ni][b]),div,time.time()-start,flush=True)
    aa,bb=np.where(ds<5e-11)
    for a,b in zip(aa,bb):
     rec=[kind,seed,n,int(os[a]),int(ks[ni][b]),div,float(ds[a,b])];print('HIT',rec,flush=True)
     with open('offset_hits.jsonl','a') as f:f.write(json.dumps(rec)+'\n')
 if j%10000==0:print('AT',j,time.time()-start,flush=True)
