from optimize import *
lib.backprop.argtypes=[np.ctypeslib.ndpointer(np.complex128,flags='C_CONTIGUOUS'),np.ctypeslib.ndpointer(np.float64,flags='C_CONTIGUOUS')]
n=int(sys.argv[1]);m=int(sys.argv[2]);kind=sys.argv[3];T=np.load('unitary_%dq.npy'%n);Th=T.conj().T.copy();N=2**n;gs=layout(n,m,kind);lib.setup(n,len(gs),gs,T);p=3*sum(gs[:,0]==0);V=np.zeros_like(T);grad=np.zeros(p);best=1.;start=time.time()
for seed in range(30):
 rng=np.random.default_rng(seed);x=rng.uniform(-np.pi,np.pi,p);ev=0
 def fun(x):
  global ev
  lib.matrix(x,V);A=Th@V@T;B=T@V@Th;f=1-np.vdot(V,A).real/N;lib.backprop(np.ascontiguousarray((A+B)*.5),grad);ev+=1
  return f,grad.copy()
 res=minimize(fun,x,jac=True,method='L-BFGS-B',options={'maxiter':1200,'ftol':1e-14,'gtol':1e-9,'maxcor':30})
 print('DONE',n,m,kind,seed,res.fun,ev,time.time()-start,flush=True)
 if res.fun<best:
  best=res.fun;np.savez('commute_%d_%d_%s.npz'%(n,m,kind),x=res.x,gates=gs,loss=res.fun)
 if res.fun<1e-9:
  lib.matrix(res.x,V)
  for r in range(-20,21):
   Vr=np.linalg.matrix_power(V,r);err=1-abs(np.vdot(T,Vr)/N)**2
   print('POWER',r,err,flush=True)
  break
