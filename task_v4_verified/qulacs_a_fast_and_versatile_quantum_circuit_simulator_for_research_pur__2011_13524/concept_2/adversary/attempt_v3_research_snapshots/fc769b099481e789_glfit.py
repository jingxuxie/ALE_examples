from optimize import *
import scipy.linalg as la
n=7;d=np.load('best_7.npz');gs=d['gates'];theta=d['x'];T=np.load('unitary_7q.npy');lib.setup(n,len(gs),gs,T);V=np.zeros_like(T);lib.matrix(theta,V);z=np.vdot(T,V)/(2**n);mats=[]
for th,ph,lam in theta.reshape(-1,3):
 c,s=np.cos(th/2),np.sin(th/2);mats.append(np.array([[c,-np.exp(1j*lam)*s],[np.exp(1j*ph)*s,np.exp(1j*(ph+lam))*c]]))
mats=np.array(mats);mats[0]*=np.conj(z)/abs(z);x=np.ascontiguousarray(mats).view(float).ravel();grad=np.zeros_like(x);lib2=ctypes.CDLL(os.path.abspath('glcore.so'));lib2.setup.argtypes=lib.setup.argtypes;lib2.calc.argtypes=[np.ctypeslib.ndpointer(np.float64,flags='C_CONTIGUOUS'),np.ctypeslib.ndpointer(np.float64,flags='C_CONTIGUOUS'),ctypes.c_double];lib2.calc.restype=ctypes.c_double;lib2.setup(n,len(gs),gs,T);start=time.time();ev=0
for lam in [.0001,.001,.01,.1,1.]:
 def fun(x):
  global ev
  f=lib2.calc(x,grad,lam);ev+=1
  if ev%100==0:print(lam,ev,f,time.time()-start,flush=True)
  return f,grad.copy()
 res=minimize(fun,x,jac=True,method='L-BFGS-B',options={'maxiter':3000,'ftol':1e-13,'gtol':1e-8,'maxcor':50});x=res.x
 print('DONE',lam,res.fun,res.nit,time.time()-start,flush=True);np.savez('gl_%g.npz'%lam,x=x,gates=gs,loss=res.fun)
