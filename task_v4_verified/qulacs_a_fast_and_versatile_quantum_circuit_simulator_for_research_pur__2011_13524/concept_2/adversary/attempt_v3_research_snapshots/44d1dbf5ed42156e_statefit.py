from optimize import layout
import os,ctypes,sys,numpy as np,time
from scipy.optimize import minimize
n,m,kind,seed0=int(sys.argv[1]),int(sys.argv[2]),sys.argv[3],int(sys.argv[4]);N=2**n;T=np.load('unitary_%dq.npy'%n);gs=layout(n,m,kind);p=3*sum(gs[:,0]==0)
cp=np.ctypeslib.ndpointer(np.complex128,flags='C_CONTIGUOUS');dp=np.ctypeslib.ndpointer(np.float64,flags='C_CONTIGUOUS');ip=np.ctypeslib.ndpointer(np.int32,flags='C_CONTIGUOUS');lib=ctypes.CDLL(os.path.abspath('statecore.so'));lib.setup.argtypes=[ctypes.c_int,ctypes.c_int,ctypes.c_int,ip,cp,cp];lib.calc.argtypes=[dp,dp,ctypes.c_int];lib.calc.restype=ctypes.c_double
rg=np.random.default_rng(157);S=rg.normal(size=(N,4))+1j*rg.normal(size=(N,4));S/=np.linalg.norm(S,axis=0);
if 'BASIS' in os.environ:
 S[:,0]=0;S[0,0]=1;S[:,1]=1/np.sqrt(N)
Y=T@S;grad=np.zeros(p);start=time.time();best=1
for seed in range(seed0,seed0+200):
 rng=np.random.default_rng(seed);x=rng.uniform(-np.pi,np.pi,p)
 for k in [1,2,4,N]:
  ss=np.ascontiguousarray(S[:,:k]) if k<N else np.eye(N,dtype=complex);yy=np.ascontiguousarray(Y[:,:k]) if k<N else T
  lib.setup(n,k,len(gs),gs,ss,yy)
  def fun(x):return lib.calc(x,grad,0),grad.copy()
  res=minimize(fun,x,jac=True,method='L-BFGS-B',options={'maxiter':2000 if k<N else 4000,'ftol':1e-12,'gtol':1e-8,'maxcor':40});x=res.x
  print(n,m,kind,seed,'k',k,'loss',res.fun,'nit',res.nit,'time',time.time()-start,flush=True)
  if k==1 and res.fun>0.15:break
  if k>1 and res.fun>0.2:break
  if k==N:
   np.savez('state_%d_%d_%s_%d.npz'%(n,m,kind,seed),x=x,gates=gs,loss=res.fun)
   if res.fun<1e-10:raise SystemExit
  if k==1 and res.fun<best:
   best=res.fun;np.savez(('basis1' if 'BASIS' in os.environ else 'state1')+'_%d_%d_%s_%d.npz'%(n,m,kind,seed0),x=x,gates=gs,loss=res.fun)
