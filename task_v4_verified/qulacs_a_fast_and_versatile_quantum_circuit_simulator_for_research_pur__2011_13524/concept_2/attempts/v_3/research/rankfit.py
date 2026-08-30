from optimize import *
import scipy.linalg as la
lib.forward_on.argtypes=[np.ctypeslib.ndpointer(np.float64,flags='C_CONTIGUOUS'),np.ctypeslib.ndpointer(np.complex128,flags='C_CONTIGUOUS'),np.ctypeslib.ndpointer(np.complex128,flags='C_CONTIGUOUS')]
lib.backprop.argtypes=[np.ctypeslib.ndpointer(np.complex128,flags='C_CONTIGUOUS'),np.ctypeslib.ndpointer(np.float64,flags='C_CONTIGUOUS')]
n=int(sys.argv[1]);fullm=int(sys.argv[2]);m=int(sys.argv[3]);kind=sys.argv[4];seed0=int(sys.argv[5]);N=2**n
T=np.load('unitary_%dq.npy'%n);fsgs=layout(n,fullm,kind);edges=fsgs[fsgs[:,0]==1,1:];rem=edges[:fullm-m];inv=edges[fullm-m:][::-1]
gs=[(0,q,0) for q in range(n)]
for q,r in inv:gs.extend([(1,q,r),(0,q,0),(0,r,0)])
gs=np.array(gs,dtype=np.int32);ranks=[]
for k in range(1,n):
 r=min(4**min(k,n-k),2**sum(min(a,b)==k-1 for a,b in rem))
 if r<4**min(k,n-k):ranks.append((k,r))
print('RANKS',ranks,flush=True)
lib.setup(n,len(gs),gs,T);p=3*sum(gs[:,0]==0);V=np.zeros_like(T);grad=np.zeros(p);start=time.time();best=100
for seed in range(seed0,seed0+5):
 rng=np.random.default_rng(seed);x=rng.uniform(-np.pi,np.pi,p);ev=0
 def fun(x):
  global ev
  lib.forward_on(x,T,V);B=np.zeros_like(T);f=0
  for k,r in ranks:
   X=V.reshape(2**(n-k),2**k,2**(n-k),2**k).transpose(1,3,0,2).reshape(4**k,-1)
   a,s,b=la.svd(X,full_matrices=False,check_finite=False);tail=(a[:,r:]*s[r:])@b[r:];f+=np.sum(s[r:]**2)/N
   B-=tail.reshape(2**k,2**k,2**(n-k),2**(n-k)).transpose(2,0,3,1).reshape(N,N)
  lib.backprop(B,grad);ev+=1
  if ev%100==0:print(n,kind,seed,ev,f,time.time()-start,flush=True)
  return f,grad.copy()
 if os.environ.get('TEST'):
  f,g=fun(x);y=x.copy();y[p//2]+=1e-6;print('GRADTEST',g[p//2],(fun(y)[0]-f)/1e-6,flush=True)
 res=minimize(fun,x,jac=True,method='L-BFGS-B',options={'maxiter':2000,'ftol':1e-14,'gtol':1e-9,'maxcor':40})
 print('DONE',n,fullm,m,kind,seed,res.fun,res.nit,time.time()-start,flush=True)
 if res.fun<best:
  best=res.fun;np.savez('rank_%d_%d_%d_%s_%d.npz'%(n,fullm,m,kind,seed0),x=res.x,gates=gs,loss=res.fun)
 if res.fun<1e-12:break
