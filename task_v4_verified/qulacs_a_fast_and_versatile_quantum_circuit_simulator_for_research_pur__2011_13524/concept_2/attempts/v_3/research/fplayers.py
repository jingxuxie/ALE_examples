import numpy as np,sys,time,json,random
kind=sys.argv[1];MAX=int(sys.argv[2]);S=1800;rows=[];labels=[]
for n in [7,8]:
 for typ in ['brick','sweep']:
  for parity in ([0,1] if typ=='brick' else [0]):
   for active in [False,True]:
    for init in [0,1]:
     for skip in ['half','full','both']:
      for order in [0,1]:
       pos=0;ic=0;mask=np.zeros(S);m=0
       def angles(q):
        global pos
        for j in range(q):mask[pos+1]=1;mask[pos+2]=1;pos+=3
       if init:angles(n)
       for l in range(30):
        ec=len(range((l+parity)%2,n-1,2)) if typ=='brick' else n-1;m+=ec
        ex=((ic+ec+1)//2-(ic+1)//2) if skip=='half' else ec*(1 if skip=='full' else 2);ic+=ec
        if order==0:pos+=ex
        angles(2*ec if active else n)
        if order==1:pos+=ex
        if (36<=m<=60 if n==7 else 49<=m<=80):rows.append(mask.copy());labels.append([n,typ,parity,active,init,skip,order,l+1,m])
M=np.array(rows);NN=np.array([a[0] for a in labels]);ph=np.array([np.angle(np.linalg.slogdet(np.load('unitary_%dq.npy'%n))[0])/(2*np.pi) for n in NN]);scale=2.**(NN-1)
seeds=list(range(MAX))+[y*10000+m*100+d for y in range(2015,2028) for m in range(1,13) for d in range(1,32)]+[0xDEADBEEF,0xC0FFEE,0xBAD5EED,0x12345678,0xCAFEBABE,123456789,1234567890,3141592,8675309,201113524]
print('PATTERNS',len(labels),flush=True);start=time.time();best=1
for j in range(0,len(seeds),128):
 batch=seeds[j:j+128];u=[]
 for seed in batch:
  if kind=='python':r=random.Random(seed);a=np.array([r.random() for _ in range(S)])
  elif kind=='legacy':a=np.random.RandomState(seed).random(S)
  else:a=np.random.default_rng(seed).random(S)
  u.append(a)
 v=np.array(u)@M.T*scale
 for div in [1,2]:
  y=v/div-ph;ds=np.abs(y-np.rint(y));idx=np.unravel_index(np.argmin(ds),ds.shape)
  if ds[idx]<best:
   best=ds[idx];print('best',best,kind,batch[idx[0]],div,labels[idx[1]],time.time()-start,flush=True)
  a,b=np.where(ds<1e-10)
  for aa,bb in zip(a,b):
   rec=[kind,batch[aa],div,labels[bb],float(ds[aa,bb])];print('HIT',rec,flush=True)
   with open('layer_hits.jsonl','a') as f:f.write(json.dumps(rec)+'\n')
 if j%12800==0:print('AT',kind,j,time.time()-start,flush=True)
