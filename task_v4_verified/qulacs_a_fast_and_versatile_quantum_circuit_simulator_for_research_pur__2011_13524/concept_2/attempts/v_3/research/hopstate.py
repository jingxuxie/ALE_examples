import os,ctypes,numpy as np,time,sys
from scipy.optimize import minimize
fn=sys.argv[1];seed=int(sys.argv[2]);d=np.load(fn);x=d['x'];gs=d['gates'];n=8;N=2**n;p=len(x);T=np.load('unitary_8q.npy');r=np.random.default_rng(157);S=r.normal(size=(N,4))+1j*r.normal(size=(N,4));S/=np.linalg.norm(S,axis=0);S=np.ascontiguousarray(S[:,:1]);Y=np.ascontiguousarray(T@S);grad=np.zeros(p)
cp=np.ctypeslib.ndpointer(np.complex128,flags='C_CONTIGUOUS');dp=np.ctypeslib.ndpointer(np.float64,flags='C_CONTIGUOUS');ip=np.ctypeslib.ndpointer(np.int32,flags='C_CONTIGUOUS');lib=ctypes.CDLL(os.path.abspath('statecore.so'));lib.setup.argtypes=[ctypes.c_int,ctypes.c_int,ctypes.c_int,ip,cp,cp];lib.calc.argtypes=[dp,dp,ctypes.c_int];lib.calc.restype=ctypes.c_double;lib.setup(n,1,len(gs),gs,S,Y)
def fun(x):return lib.calc(x,grad,0),grad.copy()
rng=np.random.default_rng(seed);f,g=fun(x);best=f;start=time.time();cur=f
for it in range(1000):
 z=x.copy();num=rng.choice([4,10,20,50,100]);ids=rng.choice(p,num,replace=False);z[ids]+=rng.normal(size=num)*rng.choice([.2,.5,1.,2.])
 res=minimize(fun,z,jac=True,method='L-BFGS-B',options={'maxiter':700,'ftol':1e-12,'gtol':1e-8,'maxcor':40})
 if res.fun<best:
  best=res.fun;np.savez('hop%d_'%seed+fn,x=res.x,gates=gs,loss=res.fun);print('BEST',it,best,time.time()-start,flush=True)
 if res.fun<cur or rng.random()<np.exp((cur-res.fun)/.0008):x=res.x;cur=res.fun
 if it%20==0:print('AT',it,cur,best,time.time()-start,flush=True)
 if best<1e-10:break
