import json
import sys
from pathlib import Path

import numpy as np

from benchmark import uniform, run


requests = [uniform('symodd22', 22, 14, 12, .8, 2., 1.5, 1.85, 'odd'),
            uniform('crit22cap6', 22, 14, 6, -1.1, 2., 1.5, .55, 'even'),
            uniform('critodd22cap6', 22, 14, 6, -1.1, 2., 1.5, .55, 'odd'),
            uniform('deep6', 22, 6, 6, -2.8, 1.2, .06, .55, 'odd'),
            uniform('fieldcrit22', 22, 14, 12, -.7, 2., 1.5, .55, 'any'),
            uniform('reversed22', 22, 14, 12, -2.4, 1.2, 1.5, .55, 'any'),
            uniform('islands22', 22, 14, 12, -2., 2., .6, 1., 'any'),
            uniform('hotbasis22', 22, 14, 12, .8, 2.8, 1.5, .55, 'even')]
requests[4]['field'] = [.002 * np.cos(site * .5) for site in range(22)]
requests[5]['field'] = [.004] * 3 + [-.004] * 19
requests[6]['mass2'][7:15] = [.8] * 8
requests[6]['field'] = [.004] * 10 + [-.004] * 12
for request in requests:
    Path(__file__).with_name(request['case_id'] + '.json').write_text(json.dumps(request))
    if len(sys.argv) > 1 and request['case_id'] not in sys.argv:
        continue
    print('PRODUCT', flush=True)
    run(request, initialization='product')
    print('CAT', flush=True)
    run(request, initialization='cat')
