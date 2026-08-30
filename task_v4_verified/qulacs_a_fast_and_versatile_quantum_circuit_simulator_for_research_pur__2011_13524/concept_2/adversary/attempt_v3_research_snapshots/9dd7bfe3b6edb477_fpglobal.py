import numpy as np,sys,time,random,json
kind=sys.argv[1];NN=int(sys.argv[2]);ph=np.array([np.angle(np.linalg.slogdet(np.load('unitary_%dq.npy'%n))[0])/(2*np.pi) for n in [7,8]]);seeds=list(range(NN))+[y*10000+m*100+d for y in range(2015,2028) for m in range(1,13) for d in range(1,32)]+[0xDEADBEEF,0xC0FFEE,0xBAD5EED,0x12345678,0xCAFEBABE,123456789,1234567890,3141592,8675309,201113524];start=time.time();best=1.;K=np.arange(1,241)
for j,seed in enumerate(seeds):
 if kind=='python':r=random.Random(seed);u=np.array([r.random() for _ in range(723)])
 elif kind=='legacy':u=np.random.RandomState(seed).random(723)
 else:u=np.random.default_rng(seed).random(723)
 cs=np.cumsum(u[:720].reshape(-1,3)[:,1:].sum(axis=1));cs1=np.cumsum(u[1:721].reshape(-1,3)[:,1:].sum(axis=1));tests=[]
 for a in [.1,.2,.3,.4,.75,.8,.9,1.1,1.2,2.5,3.,3.14,4.,5.,6.]:tests.append((('range',-a,a),(cs-K)*a/np.pi))
 for a in [1.,2.,3.,4.,6.,10.]:tests.append((('range',0,a),cs*a/(2*np.pi)))
 for a in [.1,.2,.3,.4,.5,.123,.1234,.12345,.123456,.271828,.314159,.37,.41,.23,.731,.317,.42,.7,1.234]:tests.append((('phase',a),cs+a/np.pi))
 tests.extend([(('phaserand','last1'),cs+u[3*K]/np.pi),(('phaserand','first1'),cs1+u[0]/np.pi),(('phaserand','last-1'),cs+(2*u[3*K]-1)/np.pi),(('phaserand','first-1'),cs1+(2*u[0]-1)/np.pi)])
 vals=np.array([a for label,a in tests])
 for ni,n in enumerate([7,8]):
  v=vals*(2**(n-1))-ph[ni];ds=np.abs(v-np.rint(v));a,b=np.unravel_index(ds.argmin(),ds.shape)
  if ds[a,b]<best:best=ds[a,b];print('best',best,kind,seed,n,tests[a][0],int(b+1),time.time()-start,flush=True)
  aa,bb=np.where(ds<5e-11)
  for a,b in zip(aa,bb):
   rec=[kind,seed,n,tests[a][0],int(b+1),float(ds[a,b])];print('HIT',rec,flush=True)
   with open('global_hits.jsonl','a') as f:f.write(json.dumps(rec)+'\n')
 if j%10000==0:print('AT',j,time.time()-start,flush=True)
