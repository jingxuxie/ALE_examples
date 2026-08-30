from optimize import *
import scipy.linalg as la
n=int(sys.argv[1]);seed=int(sys.argv[2]);d=np.load('best_%d.npz'%n);x=d['x'];gs=d['gates'];T=np.load('unitary_%dq.npy'%n);lib.setup(n,len(gs),gs,T);p=len(x);grad=np.zeros(p);rng=np.random.default_rng(seed);start=time.time();best=1.;cur=lib.calc(x,grad)
def fun(x):return lib.calc(x,grad),grad.copy()
for it in range(100):
 y=x.copy()
 if it%2:
  left=int(rng.integers(p));num=int(rng.integers(5,40));ids=np.arange(left,min(p,left+num))
 else:ids=rng.choice(p,int(rng.integers(5,80)),replace=False)
 y[ids]+=rng.normal(size=len(ids))*rng.choice([.1,.3,.6,1.,2.])
 res=minimize(fun,y,jac=True,method='L-BFGS-B',options={'maxiter':600,'ftol':1e-13,'gtol':1e-8,'maxcor':40})
 if res.fun<best:
  best=res.fun;np.savez('hopopt_%d_%d.npz'%(n,seed),x=res.x,gates=gs,loss=best)
 if res.fun<cur or rng.random()<np.exp((cur-res.fun)/.002):x=res.x;cur=res.fun
 print(n,seed,it,'loss',res.fun,'cur',cur,'best',best,'time',time.time()-start,flush=True)
 if best<1e-10:break
