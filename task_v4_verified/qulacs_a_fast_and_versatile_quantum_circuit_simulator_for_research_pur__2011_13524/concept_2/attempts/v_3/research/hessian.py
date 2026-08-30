from optimize import *
import scipy.linalg as la
n=int(sys.argv[1]);d=np.load('best_%d.npz'%n);x=d['x'];gs=d['gates'];T=np.load('unitary_%dq.npy'%n);lib.setup(n,len(gs),gs,T);p=len(x);g=np.zeros(p);f=lib.calc(x,g);H=np.empty((p,p));delta=1e-4;start=time.time();print('start',n,f,np.max(abs(g)),flush=True)
for j in range(p):
 y=x.copy();y[j]+=delta;lib.calc(y,g);gp=g.copy();y[j]-=2*delta;lib.calc(y,g);H[:,j]=(gp-g)/(2*delta)
H=(H+H.T)/2;w,v=la.eigh(H);print('eig',w[:20], 'zeros',sum(abs(w)<1e-8), 'time',time.time()-start,flush=True);np.savez('hessian_%d.npz'%n,w=w,v=v)
for j in range(10):
 losses=[]
 for t in [-4,-2,-1,-.5,.5,1,2,4]:
  y=x+t*v[:,j];losses.append(lib.calc(y,g))
 print('direction',j,w[j],losses,flush=True)
