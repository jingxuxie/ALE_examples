import numpy as np,sys,time,datetime,json
N=int(sys.argv[1]) if len(sys.argv)>1 else 1000000
rngname=sys.argv[2] if len(sys.argv)>2 else 'default'
phase=np.array([np.angle(np.linalg.slogdet(np.load('unitary_%dq.npy'%n))[0]) for n in [7,8]])/(2*np.pi)
seeds=list(range(N))
for y in range(2010,2028):
 for mo in range(1,13):
  for day in range(1,32):seeds.append(y*10000+mo*100+day)
seeds+= [314159,271828,8675309,201113524,123456789,20250207,20250304,20250308,20260828,20260707,20260301,20260227,2147483647,4294967295]
start=time.time();best=1;minrecord=[]
for j,seed in enumerate(seeds):
 rng=np.random.default_rng(seed) if rngname=='default' else np.random.RandomState(seed)
 u=rng.random((240,3)); cs=np.cumsum(u[:,1]+u[:,2]);
 # rotations either 2*pi or pi ranges, all counts through 240
 for div in [1,2]:
  v=cs*(64/div)-phase[0];d=np.abs(v-np.rint(v));k=np.argmin(d)
  v2=cs*(128/div)-phase[1];d2=np.abs(v2-np.rint(v2));k2=np.argmin(d2)
  if min(d[k],d2[k2])<best:
   best=min(d[k],d2[k2]);print('best',best,rngname,seed,div,'7q',k+1,d[k],'8q',k2+1,d2[k2],'sec',time.time()-start,flush=True)
  for n,ds in [(7,d),(8,d2)]:
   for k in np.where(ds<2e-9)[0]:
    rec=[n,rngname,seed,div,int(k+1),float(ds[k])];print('HIT',rec,flush=True)
    with open('fingerprint_hits.jsonl','a') as f:f.write(json.dumps(rec)+'\n')
 if j%10000==0:print('AT',rngname,j,time.time()-start,flush=True)
