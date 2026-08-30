import os,sys,time,json,ctypes
import numpy as np
from scipy.optimize import minimize
lib=ctypes.CDLL(os.path.abspath('optcore.so'))
lib.setup.argtypes=[ctypes.c_int,ctypes.c_int,np.ctypeslib.ndpointer(np.int32,flags='C_CONTIGUOUS'),np.ctypeslib.ndpointer(np.complex128,flags='C_CONTIGUOUS')]
lib.calc.argtypes=[np.ctypeslib.ndpointer(np.float64,flags='C_CONTIGUOUS'),np.ctypeslib.ndpointer(np.float64,flags='C_CONTIGUOUS')];lib.calc.restype=ctypes.c_double
lib.localcalc.argtypes=lib.calc.argtypes+[ctypes.c_int];lib.localcalc.restype=ctypes.c_double
lib.matrix.argtypes=[np.ctypeslib.ndpointer(np.float64,flags='C_CONTIGUOUS'),np.ctypeslib.ndpointer(np.complex128,flags='C_CONTIGUOUS')]
def layout(n,m,kind):
 edges=[]
 if kind.startswith('layer'):
  gates=[(0,q,0) for q in range(n)];count=0;l=0
  while count<m:
   inds=list(range(n-1))
   if kind=='layerdown' or (kind=='layeralt' and l%2):inds.reverse()
   for q in inds:
    a,b=q,q+1
    if kind=='layercz' and q%2:a,b=b,a
    if kind=='layerflip' and l%2:a,b=b,a
    gates.append((1,a,b));count+=1
    if count==m:break
   gates.extend((0,q,0) for q in range(n));l+=1
  return np.array(gates,dtype=np.int32)
 if kind.startswith('snake'):
  ed=list(range(n-1))+list(range(n-3,0,-1))
  if kind=='snakedown':ed=ed[::-1]
  edges=[(q,q+1) for l in range(100) for q in ed]
 elif kind.startswith('brick'):
  for l in range(100):
   parity=(l+(kind.endswith('1')))%2
   for q in range(parity,n-1,2):
    edges.append((q,q+1))
 elif kind.startswith('sweep'):
  for l in range(100):
   inds=list(range(n-1))
   if kind=='sweepdown' or (kind=='sweepalt' and l%2) or (kind=='sweepaltdown' and l%2==0):inds=inds[::-1]
   edges.extend((q,q+1) for q in inds)
 elif kind.startswith('repeat'):
  reps=int(kind[-1]);
  for l in range(100):
   for q in range(l%2,n-1,2):edges.extend([(q,q+1)]*reps)
 gates=[(0,q,0) for q in range(n)]
 for q,r in edges[:m]:gates.extend([(1,q,r),(0,q,0),(0,r,0)])
 return np.array(gates,dtype=np.int32)
def solve(n,m,kind,seed,iters=3000):
 T=np.load('unitary_%dq.npy'%n);gs=layout(n,m,kind);lib.setup(n,len(gs),gs,T);p=3*sum(gs[:,0]==0);rng=np.random.default_rng(seed);x=rng.uniform(-np.pi,np.pi,p)*float(os.environ.get('SIGMA',1));grad=np.zeros(p);t=time.time();best=1.;ev=0
 def fun(x):
  nonlocal best,ev
  f=lib.localcalc(x,grad,int(os.environ['LOCAL'])) if 'LOCAL' in os.environ else lib.calc(x,grad);ev+=1
  if f<best:best=f
  if ev%100==0:print(n,kind,seed,ev,'loss',f,'sec',time.time()-t,flush=True)
  return f,grad.copy()
 # initial gradient validation
 if os.environ.get('TEST'):
  f,g=fun(x);eps=1e-6
  for k in [0,p//2,p-1]:
   y=x.copy();y[k]+=eps;v,_=fun(y);print('gradient',k,g[k],(v-f)/eps)
 res=minimize(fun,x,jac=True,method='L-BFGS-B',options={'maxiter':iters,'ftol':1e-14,'gtol':1e-9,'maxcor':50})
 print('DONE',n,kind,seed,res.fun,res.nit,time.time()-t,flush=True)
 fn=('s'+os.environ['SIGMA'] if 'SIGMA' in os.environ else '')+('local'+os.environ['LOCAL'] if 'LOCAL' in os.environ else 'opt')+'_%d_%s_m%d_%d'%(n,kind,m,seed);np.savez(fn+'.npz',x=res.x,gates=gs,loss=res.fun)
 return res.fun
if __name__=='__main__':solve(int(sys.argv[1]),int(sys.argv[2]),sys.argv[3],int(sys.argv[4]),int(sys.argv[5]) if len(sys.argv)>5 else 3000)
