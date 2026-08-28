from pathlib import Path
import sys

import numpy as np

assert not Path("/pilot/private/reference/author.py").exists()
for prefix in ("/home", "/srv/home"):
    hidden = Path(prefix) / "xuandong/mnt/jingxu/ALE/tasks_v3/learning_lattice_quantum_field_theories_with_equivariant_continuous_fl__2207_00283/private"
    assert not hidden.exists()
with np.load(sys.argv[1], allow_pickle=False) as archive:
    request = dict(archive)
if str(request["operation"]) == "probe":
    phi = request["phi"]
    output = dict(velocity=np.zeros_like(phi), divergence=np.zeros(phi.shape[0]), kernel=np.zeros(phi.shape + (20,)))
    if str(request["model"]).startswith("range"):
        output.update(dlam_velocity=np.zeros_like(phi), dlam_divergence=np.zeros(phi.shape[0]))
else:
    output = dict(phi=request["phi"], logp=request["logp"])
np.savez(sys.argv[2], **output)
