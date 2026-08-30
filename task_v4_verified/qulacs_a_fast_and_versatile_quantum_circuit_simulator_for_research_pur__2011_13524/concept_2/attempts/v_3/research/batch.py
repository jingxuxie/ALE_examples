from optimize import solve
import sys
n=int(sys.argv[1]);m=int(sys.argv[2]);kind=sys.argv[3];start=int(sys.argv[4]);end=int(sys.argv[5])
for seed in range(start,end):
 f=solve(n,m,kind,seed,3000)
 if f<1e-10:break
