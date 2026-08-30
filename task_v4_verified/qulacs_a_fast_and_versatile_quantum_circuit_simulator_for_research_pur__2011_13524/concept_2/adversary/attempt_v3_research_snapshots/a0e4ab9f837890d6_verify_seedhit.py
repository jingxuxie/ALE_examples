import numpy as np,ctypes,os,itertools,time
from optimize import layout
n=7;N=2**n;m=48;seed=55168;r=np.random.default_rng(seed);init=r.random((n,3));samples=[];bits=[]
for j in range(m):
 bits.append(r.random());samples.append(r.random((2,3)))
bits=np.array(bits);samples=np.array(samples);raw=np.concatenate([init,samples.reshape(-1,3)])
cp=np.ctypeslib.ndpointer(np.complex128,flags='C_CONTIGUOUS');dp=np.ctypeslib.ndpointer(np.float64,flags='C_CONTIGUOUS');ip=np.ctypeslib.ndpointer(np.int32,flags='C_CONTIGUOUS');lib=ctypes.CDLL(os.path.abspath('statecore.so'));lib.setup.argtypes=[ctypes.c_int,ctypes.c_int,ctypes.c_int,ip,cp,cp];lib.calc.argtypes=[dp,dp,ctypes.c_int];lib.calc.restype=ctypes.c_double
T=np.ascontiguousarray(np.load('unitary_7q.npy')[:,:1]);S=np.zeros_like(T);S[0,0]=1;grad=np.zeros(raw.size);best=1.;start=time.time()
for kind in ['brick0','brick1','sweepup','sweepdown','sweepalt','snake','snakedown','random','repeat2','repeat3']:
 edge=layout(n,m,kind if kind!='random' else 'brick0');edge=edge[edge[:,0]==1,1:]
 if kind=='random':edge=np.array([[int(b*(n-1)),int(b*(n-1))+1] for b in bits])
 for dirs,order,before,initrev,swapph in itertools.product(range(6),range(2),range(2),range(2),range(2)):
  gs=[(0,q,0) for q in (range(n-1,-1,-1) if initrev else range(n))]
  for j,(q,r) in enumerate(edge):
   a,b=q,r
   flip=dirs==1 or (dirs==2 and bits[j]<.5) or (dirs==3 and bits[j]>=.5) or (dirs==4 and j%2) or (dirs==5 and (j//(n-1))%2)
   if flip:a,b=b,a
   qs=[a,b] if order else [q,r]
   if before:gs.extend((0,int(q),0) for q in qs)
   gs.append((1,int(a),int(b)))
   if not before:gs.extend((0,int(q),0) for q in qs)
  gs=np.array(gs,dtype=np.int32);lib.setup(n,1,len(gs),gs,S,T)
  for mode in range(8):
   x=raw.copy();x[:,1:]*=2*np.pi
   if mode in [1,3,5,7]:x[:,1:]-=np.pi
   if mode in [0,1]:x[:,0]=x[:,0]*2*np.pi-(np.pi if mode==1 else 0)
   if mode in [2,3]:x[:,0]*=np.pi
   if mode in [4,5]:x[:,0]=2*np.arccos(np.sqrt(x[:,0]))
   if mode in [6,7]:x[:,0]=2*np.arcsin(np.sqrt(x[:,0]))
   if swapph:x[:,[1,2]]=x[:,[2,1]]
   x=x.ravel();f=lib.calc(x,grad,0)
   if f<best:best=f;print('BEST',best,kind,dirs,order,before,initrev,swapph,mode,time.time()-start,flush=True)
   if f<1e-6:np.savez('SEED_FOUND.npz',x=x,gates=gs,loss=f);raise SystemExit
print('done best',best)
