import os

for variable in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[variable] = "1"

import argparse
import json
import time

from physics import CONTRACT_VERSION, check


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("tensor")
    arguments = parser.parse_args()
    started = time.monotonic()
    result = check(arguments.tensor)
    result["contract_version"] = CONTRACT_VERSION
    result["runtime_seconds"] = time.monotonic() - started
    print(json.dumps(result, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
