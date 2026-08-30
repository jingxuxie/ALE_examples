from optimize import *
import scipy.linalg as la,glob
T=np.load('unitary_7q.npy');start=time.time()
for fn in glob.glob('gl_*.npz'):
 d=np.load(fn);gs=d['gates'];mats=d['x'].view(np.complex128).reshape(-1,2,2);x=[]
 for a in mats:
  u,s,vh=la.svd(a);a=u@vh;t=2*np.arctan2(abs(a[1,0]),abs(a[0,0]));ph=np.angle(a[1,0])-np.angle(a[0,0]);lam=np.angle(-a[0,1])-np.angle(a[0,0]);x.extend([t,ph,lam])
 x=np.array(x);grad=np.zeros_like(x);lib.setup(7,len(gs),gs,T);print('START',fn,lib.calc(x,grad),flush=True)
 def fun(x):return lib.calc(x,grad),grad.copy()
 res=minimize(fun,x,jac=True,method='L-BFGS-B',options={'maxiter':2500,'ftol':1e-14,'gtol':1e-9,'maxcor':50});np.savez('opt_7_'+fn,x=res.x,gates=gs,loss=res.fun);print('DONE',fn,res.fun,res.nit,time.time()-start,flush=True)
