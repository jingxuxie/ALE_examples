"""Negative-control predictor with assertions about sandbox isolation."""

import os
from pathlib import Path
import resource
import socket
import sys

import numpy as np


root = "/srv/home/xuandong/mnt/jingxu/ALE/tasks_v4/the_alf_algorithms_for_lattice_fermions_project_release_2_0_documentat__2012_11914/concept_3"
for prefix in (root, root.replace("/srv/home/", "/home/")):
    for suffix in ("evaluator/hidden/heldout_labels.npz", "evaluator/hidden/generate.py", "evaluator/hidden/calibration.json", "status.json"):
        for path in (prefix + "/" + suffix, "/proc/1/root" + prefix + "/" + suffix):
            try:
                with open(path, "rb") as stream:
                    stream.read(1)
            except OSError:
                pass
            else:
                raise AssertionError("private path unexpectedly readable: " + path)
for path in ("/evaluator/hidden/heldout_labels.npz", "/submission/../evaluator/hidden/heldout_labels.npz", "/public/evaluator/hidden/heldout_labels.npz", "/home/xuandong/.ssh", "/srv/home/xuandong/.codex"):
    assert not Path(path).exists(), path
assert Path("/public/input/train_labels.npz").is_file()
assert Path("/public/input/validation_labels.npz").is_file()
for path in ("/submission/write_probe", "/public/input/write_probe"):
    try:
        with open(path, "wb") as stream:
            stream.write(b"should not be writable")
    except OSError:
        pass
    else:
        raise AssertionError("read-only mount accepted a write")
assert len(os.sched_getaffinity(0)) == 1
assert resource.getrlimit(resource.RLIMIT_AS)[1] == 2 * 1024**3
processes = [entry for entry in Path("/proc").iterdir() if entry.name.isdigit()]
assert len(processes) < 12
assert set(name for _, name in socket.if_nameindex()) <= {"lo"}
assert "OPENAI_API_KEY" not in os.environ
with np.load(sys.argv[1], allow_pickle=False) as archive:
    identifiers = archive["sample_id"]
    bins = len(archive["omega_edges"]) - 1
np.savez_compressed(sys.argv[2], sample_id=identifiers, spectral_mass=np.full((len(identifiers), bins), 1.0 / bins), low_mass_quantiles=np.tile([0.0, 0.0625, 1.0], (len(identifiers), 1)))
