import numpy as np
for n in [7,8]:
 U=np.load('unitary_%dq.npy'%n);N=2**n;idx=np.arange(N);print('TARGET',n)
 for q in [0,n//2,n-1]:
  vals=[]
  for p in [np.array([[0,1],[1,0]]),np.array([[0,-1j],[1j,0]]),np.diag([1,-1])]:
   P=np.kron(np.eye(2**(n-q-1)),np.kron(p,np.eye(2**q)));A=U.conj().T@P@U
   B=A[idx[:,None]^idx[None,:],idx[None,:]].copy()
   for r in range(n):
    V=B.reshape(N,-1,2,2**r);aa=V[:,:,0,:].copy();bb=V[:,:,1,:].copy();V[:,:,0,:]=aa+bb;V[:,:,1,:]=aa-bb
   c=np.abs(B/N);vals.append(c)
   print(q,'sparse',np.sum(c>1e-10),'of',N*N,'max',c.max(),'1e-5',np.sum(c>1e-5))
  print('maxcombo',np.sqrt(np.sum(np.array(vals)**2,axis=0)).max())
