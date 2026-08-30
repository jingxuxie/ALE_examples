import json
import sys

import continuous
import seed
from improve import SOURCE

instances = json.loads(SOURCE.read_text())['instances']
for selected in map(int, sys.argv[1:]):
    try:
        seed.recover(instances[selected], 20)
        continuous.recover(instances[selected], 180)
    except Exception as error:
        print('CASE ERROR', selected, repr(error), flush=True)
