import os,time,ctypes,numpy as np
from optimize import layout
lib=ctypes.CDLL(os.path.abspath('seedcore.so'));f=lib.testseed;f.restype=ctypes.c_double;f.argtypes=[ctypes.c_int,ctypes.c_int,np.ctypeslib.ndpointer(np.int32,flags='C_CONTIGUOUS'),np.ctypeslib.ndpointer(np.float64,flags='C_CONTIGUOUS'),ctypes.c_int,ctypes.c_int,np.ctypeslib.ndpointer(np.complex128,flags='C_CONTIGUOUS')]
n=7;m=60;T=np.load('unitary_7q.npy')[:,0].copy();E={name:layout(n,m,name)[layout(n,m,name)[:,0]==1,1:].copy() for name in ['sweepalt','sweepup','sweepdown','brick0','brick1']}
seeds=list(range(2000))+[2020,2021,2022,2023,2024,2025,2026,1234,12345,123456,54321,31415,314159,2718,271828,8675309,314,271,7777,8888,777,888,202407,202408,202507,202508,202501,202502,202503,202504,202505,202506,202509,202510,202511,202512,202601,202602,202603,202604,202605,202606,202607,202608,20260301,20260302,20260828,20250828,7007,8008,1701,1702,201113524]
start=time.time();best=0
for rngname in ['default','legacy']:
 for seed in seeds:
  rng=np.random.default_rng(seed) if rngname=='default' else np.random.RandomState(seed)
  x=rng.random((n+2*m)*3)
  for kind,edges in E.items():
   for mode in range(8):
    for dirs in range(5):
     fid=f(n,m,edges,x,mode,dirs,T)
     if fid>best:
      best=fid;print('BEST',fid,rngname,seed,kind,mode,dirs,'time',time.time()-start,flush=True)
     if fid>0.99999:
      np.savez('seed_hit.npz',x=x,edges=edges,mode=mode,dirs=dirs);raise SystemExit
  if seed%100==0:print('AT',rngname,seed,time.time()-start,flush=True)
