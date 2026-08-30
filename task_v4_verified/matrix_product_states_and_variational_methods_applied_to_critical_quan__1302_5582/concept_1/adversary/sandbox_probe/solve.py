import argparse
import json
from pathlib import Path
import numpy as np
import scipy

parser = argparse.ArgumentParser()
parser.add_argument("--request", required=True)
parser.add_argument("--output", required=True)
args = parser.parse_args()
request = json.loads(Path(args.request).read_text())
assert not Path("/public/../evaluator").exists()
assert not Path("/work/../evaluator").exists()
assert not Path("/srv/home/xuandong/mnt/jingxu/ALE/tasks_v4/matrix_product_states_and_variational_methods_applied_to_critical_quan__1302_5582/concept_1/evaluator").exists()
assert not Path("/home/xuandong/mnt/jingxu/ALE/tasks_v4/matrix_product_states_and_variational_methods_applied_to_critical_quan__1302_5582/concept_1/evaluator").exists()
assert not Path("/proc/1/root/public/../evaluator").exists()
with open(args.output, "wb") as stream:
    tensors = {}
    for site in range(request["n_sites"]):
        tensor = np.zeros((1, request["local_dim"], 1))
        tensor[0, 0, 0] = 1.0
        tensors["A%d" % site] = tensor
    np.savez(stream, **tensors)
print(json.dumps({"numpy": np.__version__, "scipy": scipy.__version__, "hidden_paths_invisible": True}))
