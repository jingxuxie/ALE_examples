import numpy as np,sys,time,json
kind=sys.argv[1];N=int(sys.argv[2]) if len(sys.argv)>2 else 100000
phase=np.array([np.angle(np.linalg.slogdet(np.load('unitary_%dq.npy'%n))[0]) for n in [7,8]])
seeds=list(range(N))+[y*10000+m*100+d for y in range(2015,2028) for m in range(1,13) for d in range(1,32)]+[1234567,12345678,123456789,314159,271828,3141592,8675309,201113524]
start=time.time();best=1
patterns=[]
if kind=='skip':
 for n in [7,8]:
  for skip in ['half','full','both']:
   for order in [0,1]:
    inds=list(range(3*n));pos=3*n;out=[]
    for c in range(100):
     extra=1 if skip=='full' or (skip=='half' and c%2==0) else (2 if skip=='both' else 0)
     if order==0:pos+=extra
     inds.extend(range(pos,pos+6));pos+=6
     if order==1:pos+=extra
     ids=np.array(inds).reshape(-1,3)[:,1:].ravel();out.append(ids)
    # rectangular masks to sum determinant for all cnot counts
    mask=np.zeros((100,1200))
    for i,ids in enumerate(out):mask[i,ids]=1
    patterns.append((n,skip,order,mask))
 # faster indexes just gather u3 columns increments, prefix
 patterns2=[]
 for n,skip,order,mask in patterns:
  pairs=[np.where(mask[0])[0]]+[np.where(mask[j]-mask[j-1])[0] for j in range(1,100)]
  patterns2.append((n,skip,order,pairs[0],np.array(pairs[1:])))
for j,seed in enumerate(seeds):
 rng=np.random.default_rng(seed)
 if kind=='normal':
  u=rng.normal(size=(240,3));cs=np.cumsum(u[:,1]+u[:,2])
  tests=[('normal'+str(scale),cs*scale) for scale in [1.,np.pi,2*np.pi,.5,.25,2.]]
 elif kind=='uniform':
  u=rng.random((240,3));cs=np.cumsum(u[:,1]+u[:,2]);counts=np.arange(1,241)
  tests=[('uniform'+str(a),(cs-counts)*2*a) for a in [1.,2.,.5,.25,1.5]]
 else:
  u=rng.random(1200);tests=[]
  for n,skip,order,first,rest in patterns2:
   cs=np.r_[u[first].sum(),u[rest].sum(axis=1)];cs=np.cumsum(cs)
   for div in [1,2]:tests.append(((n,skip,order,div),cs*2*np.pi/div))
 for label,angles in tests:
  for idx,n in enumerate([7,8]):
   if kind=='skip' and label[0]!=n:continue
   v=(angles*(2**(n-1))-phase[idx])/(2*np.pi);ds=np.abs(v-np.rint(v));k=ds.argmin()
   if ds[k]<best:
    best=ds[k];print('best',best,kind,label,seed,n,k+1,'sec',time.time()-start,flush=True)
   for k in np.where(ds<1e-10)[0]:
    rec=[kind,label,seed,n,int(k+1),float(ds[k])];print('HIT',rec,flush=True)
    with open('variant_hits.jsonl','a') as f:f.write(json.dumps(rec)+'\n')
 if j%10000==0:print('AT',kind,j,time.time()-start,flush=True)
