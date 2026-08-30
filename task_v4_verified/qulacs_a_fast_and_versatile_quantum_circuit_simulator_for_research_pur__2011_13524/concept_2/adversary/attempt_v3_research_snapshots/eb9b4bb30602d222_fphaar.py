import numpy as np,sys,time,json
kind=sys.argv[1];NN=int(sys.argv[2]);ph=np.array([np.angle(np.linalg.slogdet(np.load('unitary_%dq.npy'%n))[0])/(2*np.pi) for n in [7,8]])
seeds=list(range(NN))+[y*10000+m*100+d for y in range(2015,2028) for m in range(1,13) for d in range(1,32)]+[b+x for b in [0xC0FFEE,0xBAD5EED,0xDEADBEEF,123456789,201113524,31415926] for x in range(-20,21)]
start=time.time();best=1
for j,seed in enumerate(seeds):
 rng=np.random.default_rng(seed) if kind=='default' else np.random.RandomState(seed)
 u=rng.normal(size=(240,8));tests=[]
 for grouping in [0,1]:
  z=u[:,:4]+1j*u[:,4:] if grouping==0 else u[:,::2]+1j*u[:,1::2];det=np.angle(z[:,0]*z[:,3]-z[:,1]*z[:,2]);first=np.angle(z[:,0])
  for norm in [0,1]:
   cs=np.cumsum(det-2*norm*first)/(2*np.pi);tests.append(((grouping,norm),cs));tests.append(((grouping,norm,'neg'),-cs))
 v=u.reshape(-1,4)[:240]
 for a in range(4):
  for b in range(a+1,4):
   cs=np.cumsum(np.angle(v[:,a]+1j*v[:,b]))/np.pi;tests.append((('quat',a,b),cs));tests.append((('quat',a,b,'neg'),-cs))
 vals=np.array([x for label,x in tests])
 for ni,n in enumerate([7,8]):
  ds=vals*(2**(n-1))-ph[ni];ds=np.abs(ds-np.rint(ds));a,b=np.unravel_index(ds.argmin(),ds.shape)
  if ds[a,b]<best:best=ds[a,b];print('best',best,kind,seed,n,tests[a][0],int(b+1),time.time()-start,flush=True)
  aa,bb=np.where(ds<5e-11)
  for a,b in zip(aa,bb):
   rec=[kind,seed,n,tests[a][0],int(b+1),float(ds[a,b])];print('HIT',rec,flush=True)
   with open('haar_hits.jsonl','a') as f:f.write(json.dumps(rec)+'\n')
 if j%10000==0:print('AT',j,time.time()-start,flush=True)
