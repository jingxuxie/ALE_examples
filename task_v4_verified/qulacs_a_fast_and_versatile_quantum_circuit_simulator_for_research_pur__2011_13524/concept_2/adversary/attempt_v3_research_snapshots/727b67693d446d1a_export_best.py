import numpy as np,glob,json,sys,os
from optimize import lib
answer={}
for n,m in [(7,60),(8,80)]:
 choices=[]
 for f in glob.glob('*opt_%d_*.npz'%n):
  d=np.load(f)
  if 'x' not in d or 'gates' not in d:continue
  gs=d['gates'];p=d['x'];loss=float(d['loss'])
  if sum(gs[:,0]==1)<=m and sum(gs[:,0]==0)<=2*m+n:choices.append((loss,f))
 loss,fn=min(choices);d=np.load(fn);np.savez('best_%d.npz'%n,**{k:d[k] for k in d.files});p=d['x'];gs=d['gates'];gates=[];j=0
 for kind,q,r in gs:
  if kind:gates.append({'gate':'CNOT','control':int(q),'target':int(r)})
  else:gates.append({'gate':'U3','qubit':int(q),'theta':float(p[j]),'phi':float(p[j+1]),'lambda':float(p[j+2])});j+=3
 answer['unitary_%dq'%n]=gates
 T=np.load('unitary_%dq.npy'%n);lib.setup(n,len(gs),gs,T);V=np.zeros_like(T);lib.matrix(p,V);z=np.vdot(T,V)/(2**n);R=V.conj().T@T;ev=np.linalg.eigvals(R);ang=np.sort(np.angle(ev));print(n,fn,loss,'true',1-abs(z)**2,'mingap',np.diff(ang).min(),'traces',[round(abs(np.trace(np.linalg.matrix_power(R,j))/(2**n)),4) for j in range(1,5)])
json.dump(answer,open('best_witness.json','w'),allow_nan=False,indent=2)
