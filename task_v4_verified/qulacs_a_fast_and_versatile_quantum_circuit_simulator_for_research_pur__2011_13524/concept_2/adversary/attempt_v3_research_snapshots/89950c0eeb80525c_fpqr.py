import sys,time,json,numpy as np
N=int(sys.argv[1]) if len(sys.argv)>1 else 100000
ph=np.array([np.angle(np.linalg.slogdet(np.load('unitary_%dq.npy'%n))[0]) for n in [7,8]])/(2*np.pi)
seeds=list(range(N))+[y*10000+m*100+d for y in range(2015,2028) for m in range(1,13) for d in range(1,32)]+[0xDEADBEEF,0xC0FFEE,0xBAD5EED,0x12345678,0xCAFEBABE,123456789,1234567890,3141592,8675309,201113524]
start=time.time();best=1
for j,seed in enumerate(seeds):
 u=np.random.default_rng(seed).normal(size=(240,8));z=u[:,:4]+1j*u[:,4:];ang=np.angle(z[:,0]*z[:,3]-z[:,1]*z[:,2]);ang0=np.angle(z[:,0]);tests=[('haar',np.cumsum(ang)/(2*np.pi)),('haar_u3',np.cumsum(ang-2*ang0)/(2*np.pi)),('quaternion',np.cumsum(-2*np.angle(u.reshape(-1,4)[:240,0]+1j*u.reshape(-1,4)[:240,1]))/(2*np.pi))]
 for label,cs in tests:
  for ni,n in enumerate([7,8]):
   val=cs*(2**(n-1))-ph[ni];ds=np.abs(val-np.rint(val));k=ds.argmin()
   if ds[k]<best:best=ds[k];print('best',best,label,seed,n,k+1,time.time()-start,flush=True)
   for k in np.where(ds<1e-10)[0]:
    rec=[label,seed,n,int(k+1),float(ds[k])];print('HIT',rec,flush=True)
    with open('qr_hits.jsonl','a') as f:f.write(json.dumps(rec)+'\n')
 if j%10000==0:print('AT',j,time.time()-start,flush=True)
