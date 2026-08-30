import hashlib,zlib,datetime,json,numpy as np
seeds=set(range(20100000,20280000))
for x in range(20150000,20280000):
 for q in [7,8]:seeds.add(x*10+q);seeds.add(x*100+q)
for b in [0xC0FFEE,0xDEADBEEF,0xBAD5EED,0xCAFEBABE,0x12345678,123456789,1234567890,201113524,31415926,27182818,314159265,271828182,2026000000,2025000000,2024000000,8675309]:seeds.update(range(b-1000,b+1001))
strings=set()
for n in [7,8]:
 for pref in ['unitary','target','circuit','qulacs','quantum','random_unitary','public_unitary','dense_unitary','full_unitary','operator','public','circuit_synthesis']:
  for sep in ['','_','-',' ',':']:
   for suf in ['','q','qubits','_qubits','-qubits']:
    strings.add(pref+sep+str(n)+suf)
 strings.update([str(n),f'unitary_{n}q',f'unitary_{n}q_v1',f'unitary_{n}q_v2',f'concept_2_unitary_{n}q'])
for s in strings:
 b=s.encode();seeds.add(zlib.crc32(b));seeds.add(zlib.adler32(b))
 for alg in ['md5','sha1','sha256','sha512','blake2b']:
  d=getattr(hashlib,alg)(b).digest()
  for size in [4,8,16]:
   for e in ['little','big']:
    seeds.add(int.from_bytes(d[:size],e));seeds.add(int.from_bytes(d[-size:],e))
json.dump(sorted(seeds),open('more_seeds.json','w'));print('seeds',len(seeds))
