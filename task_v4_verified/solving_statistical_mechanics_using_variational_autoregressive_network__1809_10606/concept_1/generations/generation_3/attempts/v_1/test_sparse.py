import json
import sys
import time
import numpy as np
from sparse import exact_sparse

from audit import metrics

if len(sys.argv) == 3:
    started = time.monotonic()
    instance = json.load(open(sys.argv[1]))
    model = exact_sparse(np.asarray(instance['couplings']), np.asarray(instance['fields']))
    print('sparse time', time.monotonic() - started, 'found', model is not None, flush=True)
    if model is not None:
        json.dump(model, open(sys.argv[2], 'w'))
        print(metrics(instance, model), flush=True)
else:
    rng = np.random.default_rng(441)
    for count in [3, 6, 9]:
        couplings = np.zeros((count, count))
        if count <= 6:
            couplings = np.triu(rng.normal(0, .7, size=(count, count)), 1)
            couplings += couplings.T
        else:
            for site in range(count):
                for distance in [1, 2]:
                    other = (site + distance) % count
                    couplings[site, other] = rng.normal(0, .7)
                    couplings[other, site] = couplings[site, other]
        fields = rng.normal(0, .3, size=count)
        instance = {'n': count, 'couplings': couplings.tolist(), 'fields': fields.tolist()}
        model = exact_sparse(couplings, fields)
        assert model is not None
        result = metrics(instance, model)
        assert abs(result['kl']) < 1e-10
        assert abs(result['ess'] - 1) < 1e-10
        assert abs(result['normalization'] - 1) < 1e-10
        print(count, result, flush=True)
