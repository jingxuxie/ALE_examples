import os
os.environ['OPENBLAS_NUM_THREADS']='1';os.environ['OMP_NUM_THREADS']='1';os.environ['MKL_NUM_THREADS']='1'
import json,sys,time,ctypes
from pathlib import Path
import numpy as np
from scipy.optimize import minimize
HERE=Path(__file__).resolve().parent
lib=ctypes.CDLL(str(HERE/'fast.so'))
arr=np.ctypeslib.ndpointer
lib.evaluate.argtypes=[ctypes.c_int,ctypes.c_int,arr(dtype=np.int32,flags='C_CONTIGUOUS'),arr(dtype=np.int32,flags='C_CONTIGUOUS'),arr(dtype=np.float64,flags='C_CONTIGUOUS'),arr(dtype=np.complex128,flags='C_CONTIGUOUS'),ctypes.c_void_p,ctypes.c_void_p]
lib.evaluate.restype=ctypes.c_double
class Fit:
 def __init__(self,t,edges):
  self.t=t;self.n=t['n_qubits'];self.target=np.ascontiguousarray(np.array(t['unitary_real'])+1j*np.array(t['unitary_imag']))
  self.edges=edges;self.gates=[('u',q) for q in range(self.n)]
  for c,q in edges:self.gates += [('c',c,q),('u',c),('u',q)]
  self.qubits=np.array([g[-1] for g in self.gates],dtype=np.int32);self.ctrls=np.array([g[1] if g[0]=='c' else -1 for g in self.gates],dtype=np.int32)
  self.np=sum(3 for g in self.gates if g[0]=='u');self.calls=0
 def fun(self,x):
  grad=np.empty_like(x);self.calls+=1
  v=lib.evaluate(self.n,len(self.gates),self.qubits,self.ctrls,x,self.target,grad.ctypes.data,None)
  return v,grad
 def matrix(self,x):
  a=np.empty_like(self.target);lib.evaluate(self.n,len(self.gates),self.qubits,self.ctrls,x,self.target,None,a.ctypes.data);return a
 def witness(self,x):
  out=[];p=0
  for g in self.gates:
   if g[0]=='c':out.append(dict(gate='CNOT',control=g[1],target=g[2]))
   else:
    th,ph,la=x[p:p+3];p+=3
    out.append(dict(gate='U3',qubit=g[1],theta=float(th),phi=float(ph),**{'lambda':float(la)}))
  return out
 def save(self,x,path,info=None):
  json.dump(dict(target=self.t['id'],edges=self.edges,x=x.tolist(),loss=self.fun(x)[0],witness=self.witness(x),info=info),open(path,'w'),indent=2)
def patterns(n,m):
 chain=list(range(n-1));brick=chain[::2]+chain[1::2]
 pat={}
 for name,seq in [('sweep',chain),('reverse',chain[::-1]),('brick',brick),('brickrev',brick[::-1]),('zigzag',chain+chain[::-1]),('zigrev',chain[::-1]+chain)]:
  p=(seq*((m+len(seq)-1)//len(seq)))[:m];pat[name]=[(q,q+1) for q in p]
 return pat
if __name__=='__main__':
 data=json.load(open(sys.argv[1]));n=int(sys.argv[2]);name=sys.argv[3] if len(sys.argv)>3 else 'sweep';seed=int(sys.argv[4]) if len(sys.argv)>4 else 1
 target=next(t for t in data['targets'] if t['n_qubits']==n)
 p=patterns(n,target['max_cnot'])[name];fit=Fit(target,p);rng=np.random.default_rng(seed);best=1.;start=time.time()
 # numerical derivative check
 x=rng.normal(size=fit.np);val,gr=fit.fun(x);x1=x.copy();x1[3]+=1e-6
 print('check',n,name,gr[3],(fit.fun(x1)[0]-val)/1e-6,flush=True)
 for trial in range(100):
  if trial and trial%3 and best<0.5:
   x=bx+rng.normal(size=fit.np)*rng.choice([.15,.4,.8,1.5])
  else:x=rng.uniform(-np.pi,np.pi,fit.np)
  r=minimize(fit.fun,x,jac=True,method='L-BFGS-B',options={'maxiter':2500,'ftol':2e-14,'gtol':1e-9,'maxcor':30})
  print(n,name,seed,'trial',trial,'loss',r.fun,'nit',r.nit,'calls',fit.calls,'secs',time.time()-start,flush=True)
  if r.fun<best:
   best=r.fun;bx=r.x.copy();fit.save(bx,HERE/f'best_{n}_{name}_{seed}.json',{'trial':trial,'secs':time.time()-start})
  if best<1e-12:break
