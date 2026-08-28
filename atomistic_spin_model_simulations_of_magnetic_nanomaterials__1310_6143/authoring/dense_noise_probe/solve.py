import json
import sys
import numpy as np

case = json.load(open(sys.argv[1]))
count = int(np.prod(case['shape']))
white = np.random.default_rng(case['noise_seed']).standard_normal((count, 3, case['nfft']))
transformed = np.fft.rfft(white, axis=2)
colored = np.fft.irfft(transformed, n=case['nfft'], axis=2)
with open(sys.argv[2], 'w') as output:
    json.dump(dict(bytes_live=white.nbytes + transformed.nbytes + colored.nbytes,
        roundtrip_error=float(np.max(np.abs(white - colored)))), output)
