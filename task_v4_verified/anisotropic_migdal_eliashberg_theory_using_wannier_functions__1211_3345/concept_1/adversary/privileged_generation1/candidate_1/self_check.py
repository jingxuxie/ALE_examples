import argparse
import os
import sys
import numpy as np
from solve import Model

sys.path.insert(0, os.environ["ALE_PUBLIC_INPUT"])
from eliashberg import Model as PublicModel

parser = argparse.ArgumentParser()
parser.add_argument("--input", required=True)
parser.add_argument("--output", required=True)
arguments = parser.parse_args()
with np.load(arguments.input, allow_pickle=False) as archive:
    instance = {name: archive[name] for name in archive.files}
delta = instance["initial_delta"]
model = Model(instance)
public = PublicModel(instance)
actual_z, actual_map = model.map(delta)
expected_z, expected_map = public.map(delta)
np.testing.assert_allclose(actual_z, expected_z, rtol=3e-12, atol=3e-12)
np.testing.assert_allclose(actual_map, expected_map, rtol=3e-12, atol=3e-12)
direction = np.random.default_rng(19375).normal(size=delta.shape)
np.testing.assert_allclose(model.linearize(delta, actual_z, actual_map)(direction),
                           public.linearize(delta)(direction), rtol=3e-11, atol=3e-11)
np.savez(arguments.output, delta=actual_map, z=actual_z)
