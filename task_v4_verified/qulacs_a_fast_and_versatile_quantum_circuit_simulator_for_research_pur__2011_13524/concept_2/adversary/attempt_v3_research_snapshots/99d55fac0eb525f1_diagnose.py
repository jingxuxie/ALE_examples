import os, json, numpy as np, scipy.linalg as la
from importlib.util import find_spec
print({x:find_spec(x) is not None for x in ['torch','jax','numba','qiskit','cirq','bqskit','quimb']})
d=json.load(open(os.environ['P']+'/input/targets.json'))
np.set_printoptions(precision=4,suppress=True,linewidth=160)
for t in d['targets']:
 n=t['n_qubits']; U=np.array(t['unitary_real'])+1j*np.array(t['unitary_imag']);N=2**n
 print('\nTARGET', t['id'],'norm',la.norm(U.conj().T@U-np.eye(N)),'tr',np.trace(U),'sym',la.norm(U-U.T),'herm',la.norm(U-U.conj().T))
 np.save(t['id']+'.npy', U)
 # Schmidt ranks
 for k in range(1,n):
  X=U.reshape(2**(n-k),2**k,2**(n-k),2**k).transpose(1,3,0,2).reshape(4**k,4**(n-k))
  s=la.svdvals(X)/np.sqrt(N)
  print('cut', k, 'rank',sum(s>1e-10),'s',s[:8],s[-8:],'entropy',-sum(s*s*np.log(s*s+1e-100)))
 # Pauli causality: squared weight of evolved output local ops nontrivial on each input
 paulis=[np.array([[0,1],[1,0]]),np.array([[0,-1j],[1j,0]]),np.diag([1,-1])]
 infl=np.zeros((n,n)); scone=[]
 for q in range(n):
  cc=[]
  for p in paulis:
   P=np.kron(np.eye(2**(n-q-1)),np.kron(p,np.eye(2**q)))
   A=U.conj().T@P@U
   for j in range(n):
    B=A.reshape(2**(n-j-1),2,2**j,2**(n-j-1),2,2**j)
    B=np.trace(B,axis1=1,axis2=4).reshape(N//2,N//2)/2
    infl[q,j]+=1-la.norm(B)**2/(N/2)
  # average
 print('causality',infl/3)
