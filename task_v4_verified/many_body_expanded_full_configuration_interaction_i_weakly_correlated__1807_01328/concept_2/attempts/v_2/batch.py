import json
import subprocess
import sys
import time

import numpy as np

from search import Engine, ROOT, load


engine = Engine()
ranked = []
for path in sorted(ROOT.glob("candidate_*.json")):
    coefficients = load(path)
    increments, jacobian, tail, tail_gradient, properties = engine.evaluate(coefficients)
    bound = float(np.max(np.abs(increments) + 0.001 * np.abs(jacobian).sum(axis=1)))
    ranked.append((bound, str(path), float(np.max(np.abs(increments)))))
ranked.sort()
(ROOT / "ranked.json").write_text(json.dumps(ranked, indent=2) + "\n")
print("Ranked starts", ranked[:20], flush=True)
for index, (bound, path, maximum) in enumerate(ranked[:20]):
    name = "box_%02d" % index
    print("START", name, path, bound, time.time(), flush=True)
    with (ROOT / (name + ".log")).open("w") as stream:
        subprocess.run([sys.executable, str(ROOT / "robust.py"), path, "--box", "--sigma", "1", "--steps", "350", "--tail", "105", "--name", name], stdout=stream, stderr=subprocess.STDOUT, check=True)
    result = load(ROOT / (name + ".json"))
    print("RESULT", name, engine.summary(result), flush=True)
