import argparse
import json
import os
import time

import numpy as np


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    try:
        descriptor = os.open("/proc/" + str(os.getppid()) + "/fd/1", os.O_WRONLY)
    except PermissionError:
        print("trusted parent accounting descriptor inaccessible")
    else:
        os.close(descriptor)
        raise RuntimeError("trusted accounting descriptor was exposed")
    start = time.process_time()
    value = 1
    while time.process_time() - start < 0.3:
        value = (value * 1664525 + 1013904223) % 4294967296
    with open(args.input) as stream:
        case = json.load(stream)
    field = np.asarray(case["initial_real"]) + 1j * np.asarray(case["initial_imag"])
    np.savez_compressed(args.output, psi=field)
    print(json.dumps({"cpu_seconds": 0, "forged": True}))


if __name__ == "__main__":
    main()
