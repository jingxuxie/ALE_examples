import os

os.environ['OPENBLAS_NUM_THREADS']='1'

import time
from concurrent.futures import ProcessPoolExecutor,as_completed

from enumerate_patterns import chunk


if __name__=='__main__':
    seeds=[0,1,2,3,4,5,7,11,13,17,19,23,29,31,37,41,42,43,47,51,53,59,61,67,71,73,79,83,89,97,101,123,321,456,789,1024,1234,12345,123456,1234567,12345678,123456789,987654321,4242,424242,42424242,4242424242,2023,2024,2025,2026,2027,314159,3141592,31415926,314159265,3141592653,271828,2718281,27182818,271828182,161803398,141421356,17320508,602214076,8675309,1337,31337,65535,131071,2147483647,4294967295,2468,24680,24681357,246813579,13579,112358,11235813,123123,10101,456789,2205,15000,220515,22051500,220515000,20220527,20220530,20220531,0xDEADBEEF,0xBADC0DE,0xBAD5EED,0xC0FFEE]
    seeds+= [year*10000+month*100+day for year in [2024,2025,2026] for month,day in [(1,1),(1,17),(2,14),(3,1),(3,8),(3,14),(4,1),(4,13),(5,1),(5,17),(6,1),(6,9),(7,1),(8,1),(9,1),(10,1),(11,1),(12,1),(12,31)]]
    kinds=['default','legacy','default_perm','default_sort','default_shuffle','python','default_force_probes','default_exclude_center']
    jobs=[(seed*10,seed*10+10,kind,100,False,100,10) for seed in set(seeds) for kind in kinds]
    start=time.time()
    with ProcessPoolExecutor(max_workers=48) as executor:
        futures=[executor.submit(chunk,job) for job in jobs]
        for index,future in enumerate(as_completed(futures)):
            result=future.result()
            if index%20==0 or len(result)>4:
                print(index,time.time()-start,result,flush=True)
