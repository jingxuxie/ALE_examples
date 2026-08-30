import os
os.environ["OPENBLAS_NUM_THREADS"] = "1"
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import time
import json
import numpy as np
import optimizer
from contractor import canonicalize, hamiltonian_terms, load_mps, measure, transfer
from benchmark import make_case

request = json.loads(Path("experiments/two_wells.json").read_text())
tensors = canonicalize(load_mps("experiments/two_wells40.npz", request))
onsite, positions = hamiltonian_terms(request)
means = []
for center in range(len(tensors)):
    environment = np.ones((1, 1))
    for site, tensor in enumerate(tensors):
        environment = transfer(environment, tensor, positions[site] if site == center else None)
    means.append(environment.item())
print("two_wells position", means, flush=True)

original = optimizer.initial_state
def broken(onsite, positions, couplings, request):
    vectors = optimizer.hartree(onsite, positions, couplings, request, 1)
    return [vector.reshape(1, -1, 1) for vector in vectors], None

optimizer.initial_state = broken
for mass in (-0.5, -0.7, -0.9, -1.3):
    request = make_case("branch", 22, 14, 6, "any", mass, 2.0, 0.65, 1.0)
    request["budget_seconds"] = 40.0
    start = time.process_time()
    tensors = optimizer.optimize(request)
    print(mass, time.process_time() - start, measure(tensors, request), flush=True)
