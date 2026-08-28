import json
import os
from pathlib import Path
import subprocess
import sys

os.environ["OPENBLAS_NUM_THREADS"] = "1"
sys.dont_write_bytecode = True

import numpy as np
from solve import summarize, write_model


root = Path(__file__).resolve().parent
case = json.load(open(root.parent / "participant/input/cases/initial_interface_spring_01.json"))
write_model(case, [1.2762720155208536], root / "benchmark.model")
for kernel in ["projected", "cluster2", "cluster5", "cluster8", "cluster9", "pairs"]:
    path = root / f"benchmark_{kernel}.txt"
    subprocess.run([str(root / "sampler"), str(root / "benchmark.model"), str(path), "35", kernel], check=True)
    data = np.loadtxt(path)
    angle, torque, error = summarize(data)
    print(kernel, "torque", torque, "sem", error, "m", data[:, 5].mean(), flush=True)
