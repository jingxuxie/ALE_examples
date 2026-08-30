from optimize import *
import scipy.linalg as la
n=int(sys.argv[1]);d=np.load('best_%d.npz'%n);gs=d['gates'];x=d['x'];T=np.load('unitary_%dq.npy'%n);N=2**n;lib.setup(n,len(gs),gs,T);V=np.zeros_like(T);grad=np.zeros_like(x);start=time.time();ev=0
lib.backprop.argtypes=[np.ctypeslib.ndpointer(np.complex128,flags='C_CONTIGUOUS'),np.ctypeslib.ndpointer(np.float64,flags='C_CONTIGUOUS')]
def geo(x):
 global ev
 lib.matrix(x,V);R=V.conj().T@T;S,Q=la.schur(R,output='complex',check_finite=False);ang=np.angle(np.diag(S));inds=np.argsort(ang);a=ang[inds];c=np.arange(N);ss=a.sum()+2*np.pi*c;ss2=np.sum(a*a)+4*np.pi*np.r_[0,np.cumsum(a)[:-1]]+4*np.pi**2*c;vari=ss2/N-(ss/N)**2;k=np.argmin(vari);th=ang-ss[k]/N;th[inds[:k]]+=2*np.pi;H=(Q*th)@Q.conj().T;B=np.ascontiguousarray(1j*V@H);lib.backprop(B,grad);ev+=1
 if ev%100==0:print('GEO',n,ev,vari[k],time.time()-start,flush=True)
 return vari[k],grad.copy()
f,g=geo(x);yy=x.copy();yy[len(x)//2]+=1e-6;print('GRAD',g[len(x)//2],(geo(yy)[0]-f)/1e-6,flush=True)
for it in range(3):
 res=minimize(geo,x,jac=True,method='L-BFGS-B',options={'maxiter':500,'ftol':1e-11,'gtol':1e-8,'maxcor':40});x=res.x;print('GEODONE',it,res.fun,time.time()-start,flush=True)
 def fun(x):return lib.calc(x,grad),grad.copy()
 res=minimize(fun,x,jac=True,method='L-BFGS-B',options={'maxiter':1500,'ftol':1e-14,'gtol':1e-9,'maxcor':50});x=res.x;np.savez('opt_%d_geo%d.npz'%(n,it),x=x,gates=gs,loss=res.fun);print('DONE',n,it,res.fun,time.time()-start,flush=True)
 if res.fun<1e-10:break
