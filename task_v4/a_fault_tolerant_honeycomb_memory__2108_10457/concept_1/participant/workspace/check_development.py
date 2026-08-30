import json
import sys
from pathlib import Path

import numpy as np


request = Path(sys.argv[1]).resolve()
truth = np.load(request.parent / "development_labels" / (request.name + ".npy"), allow_pickle=False)
prediction = np.load(sys.argv[2], allow_pickle=False).reshape(-1)
if prediction.shape != truth.shape or not np.isin(prediction, [0, 1]).all():
    raise ValueError("invalid output")
print(json.dumps({"shots": len(truth), "errors": int(np.count_nonzero(prediction != truth)),
                  "logical_failure_rate": float(np.mean(prediction != truth))}))
