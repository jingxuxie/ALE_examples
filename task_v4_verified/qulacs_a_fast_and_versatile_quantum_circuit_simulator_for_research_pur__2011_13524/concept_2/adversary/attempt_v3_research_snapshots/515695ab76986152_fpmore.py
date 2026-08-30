import numpy as np,random,sys,time,json
kind=sys.argv[1];NN=int(sys.argv[2]) if len(sys.argv)>2 else 100000
ph=np.array([np.angle(np.linalg.slogdet(np.load('unitary_%dq.npy'%n))[0]) for n in [7,8]])/(2*np.pi)
seeds=list(range(NN))+[y*10000+m*100+d for y in range(2015,2028) for m in range(1,13) for d in range(1,32)]+[0xDEADBEEF,0xC0FFEE,0xBAD5EED,0x12345678,0x1234567,0xCAFEBABE,1234567,12345678,123456789,1234567890,314159,271828,3141592,8675309,201113524,20240701,20241120]
start=time.time();best=1.;K=np.arange(1,241)
for j,seed in enumerate(seeds):
 if kind=='python':
  r=random.Random(seed);u=np.array([r.random() for _ in range(724)])
 elif kind=='legacy':u=np.random.RandomState(seed).random(724)
 else:u=np.random.default_rng(seed).random(724)
 cs=np.cumsum(u[:720].reshape(240,3)[:,1:].sum(axis=1));cs1=np.cumsum(u[1:721].reshape(240,3)[:,1:].sum(axis=1));su=np.r_[0,np.cumsum(u)]
 tests=[('basic',cs),('negative',-cs),('phasefirst',cs1+2*u[0]),('phaselast',cs+2*u[3*K]),('columns',su[3*K]-su[K]),('offset1',cs1),('twoangles',su[2*K]-su[K]),('theta_phi0',su[2*K]-su[2*K-1])]
 for label,ang in tests:
  for ni,n in enumerate([7,8]):
   val=ang*(2**(n-1))-ph[ni];ds=np.abs(val-np.rint(val));k=ds.argmin()
   if ds[k]<best:
    best=ds[k];print('best',best,kind,label,seed,n,int(k+1),'sec',time.time()-start,flush=True)
   for k in np.where(ds<1e-10)[0]:
    rec=[kind,label,seed,n,int(k+1),float(ds[k])];print('HIT',rec,flush=True)
    with open('more_hits.jsonl','a') as f:f.write(json.dumps(rec)+'\n')
 if j%10000==0:print('AT',kind,j,time.time()-start,flush=True)
