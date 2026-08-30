from optimize import layout
import numpy as np,scipy.linalg as la,time,sys,ctypes,os
n,m,kind,seed=int(sys.argv[1]),int(sys.argv[2]),sys.argv[3],int(sys.argv[4]);T=np.load('unitary_%dq.npy'%n);lib=ctypes.CDLL(os.path.abspath('polar.so'));cp=np.ctypeslib.ndpointer(np.complex128,flags='C_CONTIGUOUS');ip=np.ctypeslib.ndpointer(np.int32,flags='C_CONTIGUOUS');lib.setup.argtypes=[ctypes.c_int,ctypes.c_int,ip,cp,cp];lib.env.argtypes=[ctypes.c_int,cp];lib.update.argtypes=[ctypes.c_int,cp];lib.loss.restype=ctypes.c_double;lib.getg.argtypes=[cp]
rng=np.random.default_rng(seed);edges=layout(n,m,kind);qs=np.ascontiguousarray(edges[edges[:,0]==1,1]);g=[]
for j in range(m):
 a=rng.normal(size=(4,4))+1j*rng.normal(size=(4,4));q,r=la.qr(a);g.append(q)
g=np.array(g);lib.setup(n,m,qs,T,g);H=np.zeros((4,4),complex);start=time.time()
for step in range(3000):
 lib.prepare()
 for j in range(m):
  lib.env(j,H);u,s,vh=la.svd(H,check_finite=False);G=np.ascontiguousarray(u@vh);lib.update(j,G)
 f=lib.loss()
 if step%20==0:
  print(n,m,kind,seed,step,f,time.time()-start,flush=True);lib.getg(g);np.savez('polar_%d_%d_%s_%d.npz'%(n,m,kind,seed),g=g,qs=qs,loss=f)
 if f<1e-12:break
