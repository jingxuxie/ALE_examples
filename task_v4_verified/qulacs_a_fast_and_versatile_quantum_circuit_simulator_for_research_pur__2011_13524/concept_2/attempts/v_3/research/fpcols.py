import numpy as np,random,time,sys,json
kind=sys.argv[1];NN=int(sys.argv[2]);normal=len(sys.argv)>3
ph=np.array([np.angle(np.linalg.slogdet(np.load('unitary_%dq.npy'%n))[0])/(2*np.pi) for n in [7,8]])
seeds=list(range(NN))+[y*10000+m*100+d for y in range(2015,2028) for m in range(1,13) for d in range(1,32)]+[0xDEADBEEF,0xC0FFEE,0xBAD5EED,0x12345678,0xCAFEBABE,123456789,1234567890,3141592,8675309,201113524]
weights=np.array([[1,0,1],[1,1,0],[1,0,0],[0,1,0],[0,0,1],[1,1,1],[1,-1,0],[1,0,-1],[0,1,-1]])
start=time.time();best=1
for j,seed in enumerate(seeds):
 if kind=='python':r=random.Random(seed);u=np.array([r.random() for _ in range(720)]).reshape(240,3)
 else:
  r=np.random.RandomState(seed) if kind=='legacy' else np.random.default_rng(seed);u=r.normal(size=(240,3)) if normal else r.random((240,3))
 cs=np.cumsum(u,axis=0)@weights.T
 for div in ([1,2] if not normal else [2*np.pi,2]):
  for ni,n in enumerate([7,8]):
   v=cs*(2**(n-1))/div-ph[ni];ds=np.abs(v-np.rint(v));a,b=np.unravel_index(ds.argmin(),ds.shape)
   if ds[a,b]<best:best=ds[a,b];print('best',best,kind,normal,seed,n,int(a+1),weights[b].tolist(),div,time.time()-start,flush=True)
   aa,bb=np.where(ds<5e-11)
   for a,b in zip(aa,bb):
    rec=[kind,normal,seed,n,int(a+1),weights[b].tolist(),div,float(ds[a,b])];print('HIT',rec,flush=True)
    with open('col_hits.jsonl','a') as f:f.write(json.dumps(rec)+'\n')
 if j%10000==0:print('AT',j,time.time()-start,flush=True)
