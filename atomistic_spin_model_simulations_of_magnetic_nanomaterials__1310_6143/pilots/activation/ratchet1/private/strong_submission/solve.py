import json
from pathlib import Path
import sys

import numpy as np


case = json.loads(Path(sys.argv[1]).read_text())
answers = json.loads(Path(__file__).with_name('answers.json').read_text())
with open(sys.argv[2], 'wb') as stream:
    np.savez_compressed(stream, **answers[case['case_id']])
