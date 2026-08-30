import numpy as np,scipy.linalg as la,sys,time
n=int(sys.argv[1]);rank=int(sys.argv[2]);U=np.load('unitary_%dq.npy'%n);N=2**n;k=n//2;ev,Q=la.eig(U);Qh=Q.conj().T;start=time.time();best=1
# eigvectors orthogonal for a nondegenerate unitary
for seed in range(20):
 rng=np.random.default_rng(seed);w=rng.normal(size=N)+1j*rng.normal(size=N);w-=w.mean();w/=la.norm(w)
 for it in range(1000):
  A=(Q*w)@Qh;B=A.reshape(2**(n-k),2**k,2**(n-k),2**k).transpose(1,3,0,2).reshape(4**k,-1);a,s,b=la.svd(B,full_matrices=False,check_finite=False);loss=np.sum(s[rank:]**2)
  if loss<best:
   best=loss
   if it%100==0 or loss<1e-10:print('BEST',n,rank,seed,it,loss,time.time()-start,flush=True)
   np.savez('lowcommute_%d_%d.npz'%(n,rank),w=w,Q=Q,loss=loss)
  if loss<1e-16:break
  B=(a[:,:rank]*s[:rank])@b[:rank];A=B.reshape(2**k,2**k,2**(n-k),2**(n-k)).transpose(2,0,3,1).reshape(N,N);w=np.einsum('ij,ji->i',Qh@A,Q);w-=w.mean();w/=la.norm(w)
 print('DONE',n,rank,seed,it,loss,time.time()-start,flush=True)
 if loss<1e-16:break
