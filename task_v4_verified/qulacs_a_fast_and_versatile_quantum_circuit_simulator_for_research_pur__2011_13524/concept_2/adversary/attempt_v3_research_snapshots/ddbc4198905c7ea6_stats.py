from optimize import *
import scipy.linalg as la
np.set_printoptions(precision=4,suppress=True)
for n,m in [(7,60),(8,80)]:
 T=np.load('unitary_%dq.npy'%n)
 def stats(U):
  k=n//2;D=2**n;s=la.svdvals(U.reshape(2**(n-k),2**k,2**(n-k),2**k).transpose(1,3,0,2).reshape(4**k,-1))/np.sqrt(D)
  res=[-sum(s*s*np.log(s*s+1e-100)),np.linalg.norm(s[-10:])]
  for q,j in [(0,n-1),(n-1,0)]:
   val=0
   for p in [np.array([[0,1],[1,0]]),np.array([[0,-1j],[1j,0]]),np.diag([1,-1])]:
    P=np.kron(np.eye(2**(n-q-1)),np.kron(p,np.eye(2**q)))
    A=U.conj().T@P@U;B=A.reshape(2**(n-j-1),2,2**j,2**(n-j-1),2,2**j);B=np.trace(B,axis1=1,axis2=4).reshape(D//2,D//2)/2
    val+=1-la.norm(B)**2/(D/2)
   res.append(val/3)
  return res
 print('TARGET',n,stats(T),flush=True)
 for m in ([36,48,60] if n==7 else [56,70,80]):
  for kind in ['sweepup','sweepdown','sweepalt','brick0','brick1','random']:
   vals=[]
   for seed in range(10):
    rng=np.random.default_rng(seed)
    gs=layout(n,m,kind if kind!='random' else 'sweepup')
    if kind=='random':
     for i in range(n,len(gs),3):
      q=int(rng.integers(n-1));gs[i]=[1,q,q+1];gs[i+1]=[0,q,0];gs[i+2]=[0,q+1,0]
    lib.setup(n,len(gs),gs,T);x=rng.uniform(-np.pi,np.pi,3*sum(gs[:,0]==0));U=np.zeros_like(T);lib.matrix(x,U);vals.append(stats(U))
   print(n,m,kind,np.mean(vals,axis=0),np.std(vals,axis=0),flush=True)
